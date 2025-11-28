#!/usr/bin/env python3
import pandas as pd
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
import argparse
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

# Load manually verified seeded errors (ground truth) from CSV.
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


"""
Robustly parse LLM-generated bug reports.
Handles many real-world output formats:
• Plain JSON array
• { "bugs": [...] }
• Single object (converted to 1-element list)
• JSON embedded in markdown/text (common with chat models)
• Various field names: filename/file, start_line, end_line/last_line, description/error_description

This function is tested against most openai & xai models.
"""
def load_llm_detections(json_path: Path) -> List[DetectedError]:
    errors: List[DetectedError] = []
    try:
        content = json_path.read_text(encoding="utf-8").strip()
        if not content:
            print(f"Warnung: {json_path.name} ist leer")
            return errors

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r'(\[.*\]|{.*})', content, re.DOTALL)
            if not match:
                print(f"Fehler: Kein JSON in {json_path.name}")
                return errors
            data = json.loads(match.group(1))

        if isinstance(data, dict) and "bugs" in data:
            data = data["bugs"]
        elif isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            return errors

        for item in data:
            if not isinstance(item, dict):
                continue
            filename = item.get("filename") or item.get("file")
            if not filename:
                continue
            try:
                start_line = int(item["start_line"])
                end_line = int(item.get("end_line", start_line))
            except (KeyError, ValueError, TypeError):
                continue

            severity = str(item.get("severity", "unknown"))
            desc = str(item.get("error_description", item.get("description", ""))).strip()

            errors.append(DetectedError(
                filename=extract_class_name(filename),
                start_line=start_line,
                end_line=end_line,
                severity=severity,
                error_description=desc
            ))
        print(f"  Geladen: {len(errors)} Fehler aus {json_path.name}")
    except Exception as e:
        print(f"Fehler beim Laden von {json_path.name}: {e}")
    return errors


"""
Classic lenient matching criterion used in nearly all code review and bug detection papers.
Returns True if the detection overlaps with the ground-truth interval after expanding GT by ±tolerance lines.
Equivalent to: at least one line in common after tolerance expansion.
"""
def lines_overlap(gt_start: int, gt_end: int, det_start: int, det_end: int, tolerance: int = 1) -> bool:
    return not ((gt_end + tolerance) < (det_start - tolerance) or
                (det_end + tolerance) < (gt_start - tolerance))



def strict_match(gt: GroundTruthError, det: DetectedError, tol: int = 3, iou_threshold: float = 0.30) -> bool:
    """
    Prüft, ob ein vom LLM erkannter Fehler (det) mit einem Ground Truth Fehler (gt) übereinstimmt.
    Kleine Einzeiler werden großzügiger bewertet -> LLMs schaetzen nie 100% zeilen-genau.
    """

    # Schritt 1: Dateiname überprüfen
    if gt.filename != det.filename:
        return False

    # Schritt 2: Ground Truth Größe
    gt_size = gt.end_line - gt.start_line + 1

    # Schritt 3: Dynamische Toleranz für Einzeiler
    if gt_size == 1:
        tol = max(tol, 2)
        iou_threshold = max(iou_threshold, 0.15)  # bei Einzeiler niedrigere IoU akzeptieren

    # Schritt 4: Ground Truth Bereich erweitern
    gs = max(1, gt.start_line - tol)  # Startzeile darf nicht <1 sein
    ge = gt.end_line + tol
    ds, de = det.start_line, det.end_line

    # Schritt 5: Bereichsüberprüfung
    if de < gs or ds > ge:
        return False

    # Schritt 6: IoU berechnen
    overlap = min(ge, de) - max(gs, ds) + 1
    union = max(ge, de) - min(gs, ds) + 1
    iou = overlap / union if union > 0 else 0

    if iou < iou_threshold:
        return False

    # Schritt 7: Detected Error Größe prüfen
    det_size = de - ds + 1
    if det_size <= 0:  # ungültiger Fehlerbereich
        return False
    if det_size > 40 or det_size > max(8, gt_size * 6):
        return False

    # Schritt 8: Alles in Ordnung → Match
    return True




"""
Core evaluation logic – performs TWO metrics in a single, correct, hierarchical pass:
1. Classic (lenient): lines_overlap with ±1 line tolerance + greedy backward assignment
2. Strict (IoU≥0.3 + size limits): only applied to predictions that already passed classic matching
→ any classic TP in classic that fails strict criteria is counted as FP in the strict metric.
"""
def match_errors_both(gt_errors: List[GroundTruthError], det_errors: List[DetectedError], tolerance: int):
    gt_by_file = defaultdict(list)
    det_by_file = defaultdict(list)
    for gt in gt_errors:
        gt_by_file[gt.filename].append(gt)
    for det in det_errors:
        det_by_file[det.filename].append(det)

    # Containers for both evaluation regimes
    tp_old_all, fp_old_all, fn_old_all = [], [], []
    tp_strict_all, fp_strict_all, fn_strict_all = [], [], []

    for filename in set(gt_by_file.keys()) | set(det_by_file.keys()):
        current_gt = gt_by_file[filename]
        current_det = det_by_file.get(filename, [])
        current_det = sorted(current_det, key=lambda x: x.start_line)

        # Two independent remaining lists – one for each metric
        remaining_old = current_gt.copy()
        remaining_strict = current_gt.copy()

        for det in current_det:
            matched_old = False
            matched_strict = False
            gt_matched_idx = -1
            matched_gt = None

            # Greedy backward: try to match the last (highest line) remaining GT first
            for i in range(len(remaining_old) - 1, -1, -1):
                gt = remaining_old[i]
                old_ok = lines_overlap(gt.start_line, gt.end_line, det.start_line, det.end_line, tolerance)
                strict_ok = strict_match(gt, det, tol=tolerance)

                # Classic True Positive
                if old_ok:
                    matched_gt = gt
                    tp_old_all.append({
                        "gt_id": gt.id,
                        "filename": gt.filename,
                        "gt_lines": (gt.start_line, gt.end_line),
                        "det_lines": (det.start_line, det.end_line),
                        "error_description": gt.error_description
                    })
                    matched_old = True
                    gt_matched_idx = i

                    # Strict True Positive only if strict criteria are met
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
                    break   # greedy: stop at first (last) compatible GT

            # Consume GT for classic metric if matched
            if matched_old:
                remaining_old.pop(gt_matched_idx)

            # False positives
            if not matched_old:
                fp_old_all.append({
                    "filename": det.filename,
                    "det_lines": (det.start_line, det.end_line),
                    "error_description": det.error_description
                })
            # includes cases where classic TP but strict fails,...correctly counted as strict FP
            if not matched_strict:
                fp_strict_all.append({
                    "filename": det.filename,
                    "det_lines": (det.start_line, det.end_line),
                    "error_description": det.error_description
                })

        # False negatives = remaining unmatched ground-truth errors
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

# Metric calculation
def calculate_metrics(tp: int, fp: int, fn: int) -> Dict[str, Any]:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}

# Print Report
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
    print(f"{'Streng (IoU≥0.3)':<18} {ms['tp']:6} {ms['fp']:6} {ms['fn']:6} {ms['precision']:10.3f} {ms['recall']:10.3f} {ms['f1']:10.3f}")
    print("═"*100)

# Save Report
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

# Detect category by filename
def detect_category(filename: str) -> str:
    name = filename.lower()

    if name.startswith("opencode_"):
        model = name[len("opencode_"):].split("_fault_bugs_")[0]
        return f"Opencode ({model})"
    else:
        model = name.split("_fault_bugs_")[0]
        return f"Raw LLM ({model})"


def main():
    parser = argparse.ArgumentParser(description="LLM Code Review Evaluation – Final Version")
    parser.add_argument("--experiment-dir", type=str, default="docs/experiment")
    parser.add_argument("--tolerance", type=int, default=1)
    parser.add_argument("--gt-csv", type=str, default="ground_truth/seeded_errors_iso25010.csv")
    parser.add_argument("--model", type=str, help="Filter nach Modell")
    args = parser.parse_args()

    base_path = Path(args.experiment_dir).resolve()
    gt_path = base_path / args.gt_csv
    if not gt_path.exists():
        raise FileNotFoundError(f"Ground Truth nicht gefunden: {gt_path}")

    result_files = sorted(base_path.glob("results/*fault_bugs_*.json"))
    if not result_files:
        raise FileNotFoundError("Keine *fault_bugs_*.json Dateien gefunden!")

    gt_errors = load_ground_truth(gt_path)
    output_dir = base_path / "analysis"
    output_dir.mkdir(exist_ok=True)

    # Sammle F1 pro Run
    f1_classic_per_run = {}
    f1_strict_per_run = {}

    overall_classic = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "runs": 0})
    overall_strict = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "runs": 0})

    print(f"Gefundene Runs: {len(result_files)}\n")

    for json_file in result_files:
        category = detect_category(json_file.name)
        if args.model and args.model.lower() not in category.lower():
            continue

        run_name = json_file.stem
        print(f"→ {json_file.name}  →  {category}")

        det_errors = load_llm_detections(json_file)
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

    # Finale Tabelle + CSV + Markdown
    results = []

    print("\n" + "═"*120)
    print(" GESAMTVERGLEICH – KLASSISCH vs. STRENG (IoU≥0.3 + Anti-Cheating) ".center(120))
    print("═"*120)
    print(f"{'Kategorie':<35} {'Typ':<12} {'Runs':>5} {'TP':>6} {'FP':>6} {'FN':>6} {'Prec':>8} {'Rec':>8} {'F1':>12} {'F1 ±σ':<12}")
    print("─"*120)

    for cat in sorted(set(overall_classic.keys()) | set(overall_strict.keys())):
        mc = calculate_metrics(overall_classic[cat]["tp"], overall_classic[cat]["fp"], overall_classic[cat]["fn"])
        ms = calculate_metrics(overall_strict[cat]["tp"], overall_strict[cat]["fp"], overall_strict[cat]["fn"])
        runs = overall_classic[cat]["runs"]

        f1_c_list = f1_classic_per_run.get(cat, [])
        f1_s_list = f1_strict_per_run.get(cat, [])
        f1_c_mean = mean(f1_c_list) if f1_c_list else 0
        f1_s_mean = mean(f1_s_list) if f1_s_list else 0
        f1_c_std = stdev(f1_c_list) if len(f1_c_list) > 1 else 0
        f1_s_std = stdev(f1_s_list) if len(f1_s_list) > 1 else 0

        print(f"{cat:<35} {'Klassisch':<12} {runs:5} {mc['tp']:6} {mc['fp']:6} {mc['fn']:6} "
              f"{mc['precision']:8.3f} {mc['recall']:8.3f} {f1_c_mean:8.3f}   ±{f1_c_std:6.3f}")
        print(f"{'':<35} {'Streng':<12} {runs:5} {ms['tp']:6} {ms['fp']:6} {ms['fn']:6} "
              f"{ms['precision']:8.3f} {ms['recall']:8.3f} {f1_s_mean:8.3f}   ±{f1_s_std:6.3f}")
        print("─"*120)

        results.append({
            "Kategorie": cat, "Typ": "Klassisch", "Runs": runs,
            "TP": mc["tp"], "FP": mc["fp"], "FN": mc["fn"],
            "Precision": round(mc["precision"], 3), "Recall": round(mc["recall"], 3),
            "F1": round(f1_c_mean, 3), "F1_Std": round(f1_c_std, 3)
        })
        results.append({
            "Kategorie": "", "Typ": "Streng", "Runs": runs,
            "TP": ms["tp"], "FP": ms["fp"], "FN": ms["fn"],
            "Precision": round(ms["precision"], 3), "Recall": round(ms["recall"], 3),
            "F1": round(f1_s_mean, 3), "F1_Std": round(f1_s_std, 3)
        })

    # CSV + Markdown
    df_results = pd.DataFrame(results)
    df_results.to_csv(output_dir / "final_comparison.csv", index=False)

    markdown = df_results.to_markdown(index=False)
    (output_dir / "final_comparison.md").write_text(markdown, encoding="utf-8")

    print(f"\nFertig! Alle Ergebnisse + final_comparison.csv + final_comparison.md in: {output_dir}")


if __name__ == "__main__":
    main()