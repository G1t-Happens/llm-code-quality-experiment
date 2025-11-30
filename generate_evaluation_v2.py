#!/usr/bin/env python3
import pandas as pd
import re
import math
import argparse
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from collections import defaultdict
from statistics import mean, stdev


@dataclass
class GroundTruthError:
    id: str
    filename: str
    start_line: int
    end_line: int
    iso_category: str
    error_description: str
    severity: str
    context_hash: str = ""


@dataclass
class DetectedError:
    filename: str
    start_line: int
    end_line: int
    severity: str
    error_description: str


def extract_class_name(filename: str) -> str:
    return Path(filename).name


# Load manually verified seeded errors (ground truth) from CSV
def load_ground_truth(csv_path: Path) -> List[GroundTruthError]:
    df = pd.read_csv(csv_path)
    required = {"id", "filename", "start_line", "end_line", "iso_category", "error_description", "severity"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Ground Truth CSV fehlt Spalten: {missing}")

    return [
        GroundTruthError(
            id=str(row["id"]),
            filename=extract_class_name(row["filename"]),
            start_line=int(row["start_line"]),
            end_line=int(row["end_line"]),
            iso_category=str(row["iso_category"]),
            error_description=str(row["error_description"]),
            severity=str(row["severity"]),
            context_hash=str(row.get("context_hash", ""))
        )
        for _, row in df.iterrows()
    ]


# Load only semantically correct & verified detections from CSV in /Detected/
def load_verified_detections(csv_path: Path) -> List[DetectedError]:
    errors: List[DetectedError] = []
    try:
        df = pd.read_csv(csv_path)

        # Normalize column name for semantically_correct_detected
        sem_col = next((col for col in df.columns if col.lower() == "semantically_correct_detected"), None)
        if sem_col is None:
            print(f"Warnung: Keine Spalte 'semantically_correct_detected' in {csv_path.name} → alle Zeilen werden übersprungen")
            return errors

        # Filter: only rows where semantically_correct_detected is true/TRUE
        df[sem_col] = df[sem_col].astype(str).str.strip()
        df_verified = df[df[sem_col].str.upper() == "TRUE"]

        print(f"  Geladen: {len(df_verified)} verifizierte Fehler aus {csv_path.name} (von insgesamt {len(df)} Zeilen)")

        for _, row in df_verified.iterrows():
            filename = row["filename"]
            if not filename:
                continue
            try:
                start_line = int(row["start_line"])
                end_line = int(row["end_line"])
            except (KeyError, ValueError, TypeError) as e:
                print(f"    Überspringe Zeile (ungültige Zeilen): {e}")
                continue

            severity = "unknown"
            desc = str(row.get("error_description", "")).strip()

            errors.append(DetectedError(
                filename=extract_class_name(filename),
                start_line=start_line,
                end_line=end_line,
                severity=severity,
                error_description=desc
            ))
    except Exception as e:
        print(f"Fehler beim Laden von {csv_path.name}: {e}")
    return errors


def lines_overlap(gt_start: int, gt_end: int, det_start: int, det_end: int, tolerance: int = 1) -> bool:
    return not ((gt_end + tolerance) < (det_start - tolerance) or
                (det_end + tolerance) < (gt_start - tolerance))


def calculate_iou(gt_start: int, gt_end: int, det_start: int, det_end: int) -> float:
    overlap_start = max(gt_start, det_start)
    overlap_end = min(gt_end, det_end)
    if overlap_start > overlap_end:
        return 0.0
    overlap = overlap_end - overlap_start + 1
    union = max(gt_end, det_end) - min(gt_start, det_start) + 1
    return overlap / union if union > 0 else 0.0


def strict_match(gt: GroundTruthError, det: DetectedError, tol: int = 3) -> bool:
    if gt.filename != det.filename:
        return False

    if not lines_overlap(gt.start_line, gt.end_line, det.start_line, det.end_line, tol):
        return False

    gt_start, gt_end = gt.start_line, gt.end_line
    det_start, det_end = det.start_line, det.end_line

    gt_size = gt_end - gt_start + 1
    det_size = det_end - det_start + 1

    iou = calculate_iou(gt_start, gt_end, det_start, det_end)

    if gt_size == 1:
        return det_size <= 7 and iou >= 0.15

    min_iou = max(0.2, 0.6 - 0.35 * math.log10(gt_size))
    max_det_size = min(gt_size * 5 + 15, gt_size * 3 + 60)

    gt_center = (gt_start + gt_end) / 2
    det_center = (det_start + det_end) / 2
    center_deviation = abs(gt_center - det_center)
    max_allowed_shift = gt_size * 1.5 + 5

    good_alignment = center_deviation <= max_allowed_shift

    return (
            iou >= min_iou
            and det_size <= max_det_size
            and good_alignment
            and det_size >= 1
    )


def match_errors_both(gt_errors: List[GroundTruthError], det_errors: List[DetectedError], tolerance: int):
    gt_by_file = defaultdict(list)
    det_by_file = defaultdict(list)
    for gt in gt_errors:
        gt_by_file[gt.filename].append(gt)
    for det in det_errors:
        det_by_file[det.filename].append(det)

    tp_old_all, fp_old_all, fn_old_all = [], [], []
    tp_strict_all, fp_strict_all, fn_strict_all = [], [], []

    for filename in set(gt_by_file.keys()) | set(det_by_file.keys()):
        current_gt = gt_by_file[filename]
        current_det = det_by_file.get(filename, [])
        current_det = sorted(current_det, key=lambda x: x.start_line)

        remaining_old = current_gt.copy()
        remaining_strict = current_gt.copy()

        for det in current_det:
            matched_old = False
            matched_strict = False
            gt_matched_idx = -1

            for i in range(len(remaining_old) - 1, -1, -1):
                gt = remaining_old[i]
                old_ok = lines_overlap(gt.start_line, gt.end_line, det.start_line, det.end_line, tolerance)
                strict_ok = strict_match(gt, det, tol=tolerance)

                if old_ok:
                    tp_old_all.append({
                        "gt_id": gt.id,
                        "filename": gt.filename,
                        "gt_lines": (gt.start_line, gt.end_line),
                        "det_lines": (det.start_line, det.end_line),
                        "error_description": gt.error_description
                    })
                    matched_old = True
                    gt_matched_idx = i

                    if strict_ok:
                        tp_strict_all.append({
                            "gt_id": gt.id,
                            "filename": gt.filename,
                            "gt_lines": (gt.start_line, gt.end_line),
                            "det_lines": (det.start_line, det.end_line),
                            "error_description": gt.error_description
                        })
                        matched_strict = True
                        remaining_strict.pop(i)
                    break

            if matched_old:
                remaining_old.pop(gt_matched_idx)

            if not matched_old:
                fp_old_all.append({
                    "filename": det.filename,
                    "det_lines": (det.start_line, det.end_line),
                    "error_description": det.error_description
                })
            if not matched_strict:
                fp_strict_all.append({
                    "filename": det.filename,
                    "det_lines": (det.start_line, det.end_line),
                    "error_description": det.error_description
                })

        for gt in remaining_old:
            fn_old_all.append({
                "gt_id": gt.id,
                "filename": gt.filename,
                "gt_lines": (gt.start_line, gt.end_line),
                "error_description": gt.error_description
            })
        for gt in remaining_strict:
            fn_strict_all.append({
                "gt_id": gt.id,
                "filename": gt.filename,
                "gt_lines": (gt.start_line, gt.end_line),
                "error_description": gt.error_description
            })

    return (tp_old_all, fp_old_all, fn_old_all), (tp_strict_all, fp_strict_all, fn_strict_all)


def calculate_metrics(tp: int, fp: int, fn: int) -> Dict[str, Any]:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def print_dual_report(category: str, old: tuple, strict: tuple, tolerance: int):
    (tp_o, fp_o, fn_o), (tp_s, fp_s, fn_s) = old, strict
    mo = calculate_metrics(len(tp_o), len(fp_o), len(fn_o))
    ms = calculate_metrics(len(tp_s), len(fp_s), len(fn_s))

    print("\n" + "═"*100)
    print(f" EVALUATION: {category} ".center(100))
    print("═"*100)
    print(f"Toleranz: ±{tolerance} Zeilen")
    print(f"{'Methode':<18} {'TP':>6} {'FP':>6} {'FN':>6} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print("─"*100)
    print(f"{'Klassisch (±1)':<18} {mo['tp']:6} {mo['fp']:6} {mo['fn']:6} {mo['precision']:10.3f} {mo['recall']:10.3f} {mo['f1']:10.3f}")
    print(f"{'Streng (IoU)':<18} {ms['tp']:6} {ms['fp']:6} {ms['fn']:6} {ms['precision']:10.3f} {ms['recall']:10.3f} {ms['f1']:10.3f}")
    print("═"*100)


def save_dual_results(category: str, run_name: str, old_res: tuple, strict_res: tuple, output_dir: Path):
    safe_cat = category.replace("(", "").replace(")", "").replace(" ", "_")
    run_dir = output_dir / safe_cat / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    (tp_o, fp_o, fn_o), (tp_s, fp_s, fn_s) = old_res, strict_res

    if tp_o: pd.DataFrame(tp_o).to_csv(run_dir / "tp_classic.csv", index=False)
    if fp_o: pd.DataFrame(fp_o).to_csv(run_dir / "fp_classic.csv", index=False)
    if fn_o: pd.DataFrame(fn_o).to_csv(run_dir / "fn_classic.csv", index=False)
    if tp_s: pd.DataFrame(tp_s).to_csv(run_dir / "tp_strict.csv", index=False)
    if fp_s: pd.DataFrame(fp_s).to_csv(run_dir / "fp_strict.csv", index=False)
    if fn_s: pd.DataFrame(fn_s).to_csv(run_dir / "fn_strict.csv", index=False)

    summary = {
        "classic": calculate_metrics(len(tp_o), len(fp_o), len(fn_o)),
        "strict": calculate_metrics(len(tp_s), len(fp_s), len(fn_s)),
        "category": category,
        "run": run_name
    }
    (run_dir / "summary_dual.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))


def detect_category_from_path(csv_path: Path) -> str:
    parts = csv_path.parts
    try:
        raw_llm_idx = parts.index("Raw_LLM")
        model = parts[raw_llm_idx + 1] if raw_llm_idx + 1 < len(parts) else "unknown"
        return f"Raw LLM ({model})"
    except ValueError:
        model = csv_path.stem.split("_fault_bugs_")[0]
        return f"Raw LLM ({model})"


def main():
    parser = argparse.ArgumentParser(description="LLM Code Review Evaluation – FINAL (CSV Detected Only)")
    parser.add_argument("--experiment-dir", type=str, default="docs/experiment")
    parser.add_argument("--tolerance", type=int, default=1)
    parser.add_argument("--gt-csv", type=str, default="ground_truth/seeded_errors_iso25010.csv")
    parser.add_argument("--model", type=str, help="Filter nach Modell (z.B. gpt-4o)")
    args = parser.parse_args()

    base_path = Path(args.experiment_dir).resolve()
    gt_path = base_path / args.gt_csv
    if not gt_path.exists():
        raise FileNotFoundError(f"Ground Truth nicht gefunden: {gt_path}")

    # ← HIER FEHLTE DAS LADEN DER GROUND TRUTH!
    gt_errors = load_ground_truth(gt_path)          # <--- DAS FEHLTE!
    output_dir = base_path / "analysis"
    output_dir.mkdir(exist_ok=True)

    f1_classic_per_run = {}
    f1_strict_per_run = {}
    overall_classic = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "runs": 0})
    overall_strict = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "runs": 0})


    pattern = "analysis/Detected/**/detected_errors.csv"
    detected_csv_files = sorted([p for p in base_path.rglob("detected_errors.csv")
                                 if "_fault_bugs_" in "".join(p.parts)])

    if not detected_csv_files:
        print("FEHLER: Keine detected_errors.csv mit '_fault_bugs_' im Pfad gefunden!")
        print("Gefundene detected_errors.csv (werden ignoriert):")
        print("\nInhalt von analysis/Detected/ (rekursiv):")
        for p in base_path.rglob("detected_errors.csv"):
            print(f"   → {p.relative_to(base_path)}")
        raise FileNotFoundError("Keine passenden Dateien gefunden!")
    print(f"Erfolgreich {len(detected_csv_files)} verifizierte Runs gefunden:\n")
    for f in detected_csv_files:
        print(f"   → {f.relative_to(base_path)}")
    print()


    def detect_category_from_path(csv_path: Path) -> str:
        path_str = str(csv_path)
        # Suche nach: Detected/<prefix>/<model>_fault_bugs_...
        match = re.search(r"Detected[\/\\]([^\/\\]+?)[\/\\].*?_fault_bugs_", path_str)
        if match:
            prefix_part = match.group(1)
            model = prefix_part.split("_")[-1]
            if "raw" in prefix_part.lower():
                return f"Raw LLM ({model})"
            elif "opencode" in prefix_part.lower():
                return f"Opencode ({model})"
            elif "finetuned" in prefix_part.lower():
                return f"FineTuned ({model})"
            else:
                return f"{prefix_part} ({model})"
        # Fallback
        return f"Detected ({csv_path.parts[-3]})"

    for csv_file in detected_csv_files:
        category = detect_category_from_path(csv_file)
        if args.model and args.model.lower() not in category.lower():
            continue

        run_name = csv_file.parent.name
        print(f"→ {csv_file.name}  →  {category}")

        det_errors = load_verified_detections(csv_file)
        old_res, strict_res = match_errors_both(gt_errors, det_errors, tolerance=args.tolerance)

        print_dual_report(category, old_res, strict_res, args.tolerance)
        save_dual_results(category, run_name, old_res, strict_res, output_dir)

        to, fo, fno = old_res
        ts, fs, fns = strict_res

        overall_classic[category]["tp"] += len(to)
        overall_classic[category]["fp"] += len(fo)
        overall_classic[category]["fn"] += len(fno)
        overall_classic[category]["runs"] += 1

        overall_strict[category]["tp"] += len(ts)
        overall_strict[category]["fp"] += len(fs)
        overall_strict[category]["fn"] += len(fns)
        overall_strict[category]["runs"] += 1

        f1_c = calculate_metrics(len(to), len(fo), len(fno))["f1"]
        f1_s = calculate_metrics(len(ts), len(fs), len(fns))["f1"]
        f1_classic_per_run.setdefault(category, []).append(f1_c)
        f1_strict_per_run.setdefault(category, []).append(f1_s)

    # Final report
    results = []

    print("\n" + "═" * 150)
    print(" GESAMTVERGLEICH – KLASSISCH (overlap) vs. STRENG (dynam. IoU) ".center(150))
    print("═" * 150)
    print(f"{'Kategorie':<55} {'Typ':<18} {'Runs':>5} {'TP':>6} {'FP':>6} {'FN':>6} {'Prec':>8} {'Rec':>8} {'F1':>10} {'F1 ±σ':>10}")
    print("─" * 150)

    for cat in sorted(set(overall_classic.keys()) | set(overall_strict.keys())):
        mc = calculate_metrics(overall_classic[cat]["tp"], overall_classic[cat]["fp"], overall_classic[cat]["fn"])
        ms = calculate_metrics(overall_strict[cat]["tp"], overall_strict[cat]["fp"], overall_strict[cat]["fn"])
        runs = overall_classic[cat]["runs"]

        f1_c_list = f1_classic_per_run.get(cat, [])
        f1_s_list = f1_strict_per_run.get(cat, [])

        f1_c_mean = mean(f1_c_list) if f1_c_list else 0.0
        f1_s_mean = mean(f1_s_list) if f1_s_list else 0.0
        f1_c_std  = stdev(f1_c_list) if len(f1_c_list) > 1 else 0.0
        f1_s_std  = stdev(f1_s_list) if len(f1_s_list) > 1 else 0.0

        print(f"{cat:<55} {'Klassisch (overlap)':<18} {runs:5} {mc['tp']:6} {mc['fp']:6} {mc['fn']:6} "
            f"{mc['precision']:8.3f} {mc['recall']:8.3f} {f1_c_mean:8.3f}   ±{f1_c_std:6.3f}")

        print(f"{'':<55} {'Streng (dynam. IoU)':<18} {runs:5} {ms['tp']:6} {ms['fp']:6} {ms['fn']:6} "
            f"{ms['precision']:8.3f} {ms['recall']:8.3f} {f1_s_mean:8.3f}   ±{f1_s_std:6.3f}")

        print("─" * 150)

        results.append({
            "Kategorie": cat, "Typ": "Klassisch(overlap)", "Runs": runs,
            "TP": mc["tp"], "FP": mc["fp"], "FN": mc["fn"],
            "Precision": round(mc["precision"], 3), "Recall": round(mc["recall"], 3),
            "F1": round(f1_c_mean, 3), "F1_Std": round(f1_c_std, 3)
        })
        results.append({
            "Kategorie": "", "Typ": "Streng(dynam. IoU)", "Runs": runs,
            "TP": ms["tp"], "FP": ms["fp"], "FN": ms["fn"],
            "Precision": round(ms["precision"], 3), "Recall": round(ms["recall"], 3),
            "F1": round(f1_s_mean, 3), "F1_Std": round(f1_s_std, 3)
        })

    df_results = pd.DataFrame(results)
    df_results.to_csv(output_dir / "final_comparison.csv", index=False)
    markdown = df_results.to_markdown(index=False)
    (output_dir / "final_comparison.md").write_text(markdown, encoding="utf-8")

    print(f"\nFertig! Alle Ergebnisse in: {output_dir}")


if __name__ == "__main__":
    import json
    main()