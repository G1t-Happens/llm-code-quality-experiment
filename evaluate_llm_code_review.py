#!/usr/bin/env python3
import pandas as pd
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
import argparse
from collections import defaultdict


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


# ──────────────────────────────────────────────────────────────
# Laden der Ground Truth
# ──────────────────────────────────────────────────────────────
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


# ──────────────────────────────────────────────────────────────
# Laden der LLM-Ergebnisse
# ──────────────────────────────────────────────────────────────
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


# ──────────────────────────────────────────────────────────────
# 1. Klassische Überlappung (±tolerance)
# ──────────────────────────────────────────────────────────────
def lines_overlap(gt_start: int, gt_end: int, det_start: int, det_end: int, tolerance: int = 1) -> bool:
    return not ((gt_end + tolerance) < (det_start - tolerance) or
                (det_end + tolerance) < (gt_start - tolerance))


# ──────────────────────────────────────────────────────────────
# 2. Strenge Lokalisierung (IoU + Anti-Cheating)
# ──────────────────────────────────────────────────────────────
def strict_match(gt: GroundTruthError, det: DetectedError, tol: int = 2) -> bool:
    if gt.filename != det.filename:
        return False

    gs, ge = gt.start_line - tol, gt.end_line + tol
    ds, de = det.start_line, det.end_line

    if de < gs or ds > ge:
        return False

    overlap = min(ge, de) - max(gs, ds) + 1
    union = max(ge, de) - min(gs, ds) + 1
    iou = overlap / union if union > 0 else 0

    gt_size = gt.end_line - gt.start_line + 1
    det_size = de - ds + 1

    # Strafe für riesige Bereiche
    if det_size > 40 or det_size > max(8, gt_size * 6):
        return False

    return iou >= 0.30


# ──────────────────────────────────────────────────────────────
# Beide Matcher parallel (greedy 1:1)
# ──────────────────────────────────────────────────────────────
def match_errors_both(gt_errors: List[GroundTruthError], det_errors: List[DetectedError], tolerance: int):
    tp_old, fp_old = [], []
    tp_strict, fp_strict = [], []
    remaining_old = gt_errors.copy()
    remaining_strict = gt_errors.copy()

    for det in det_errors:
        matched_old = False
        matched_strict = False
        gt_matched_idx = -1

        for i in range(len(remaining_old) - 1, -1, -1):
            gt = remaining_old[i]

            old_ok = (gt.filename == det.filename and
                      lines_overlap(gt.start_line, gt.end_line, det.start_line, det.end_line, tolerance))
            strict_ok = strict_match(gt, det, tol=tolerance)

            if old_ok:
                tp_old.append({
                    "gt_id": gt.id, "filename": gt.filename,
                    "gt_lines": (gt.start_line, gt.end_line),
                    "det_lines": (det.start_line, det.end_line)
                })
                matched_old = True
                gt_matched_idx = i

                if strict_ok:
                    tp_strict.append({
                        "gt_id": gt.id, "filename": gt.filename,
                        "gt_lines": (gt.start_line, gt.end_line),
                        "det_lines": (det.start_line, det.end_line)
                    })
                    matched_strict = True
                    remaining_strict.pop(i)
                break

        if matched_old:
            remaining_old.pop(gt_matched_idx)

        if not matched_old:
            fp_old.append({"filename": det.filename, "det_lines": (det.start_line, det.end_line)})
        if not matched_strict:
            fp_strict.append({"filename": det.filename, "det_lines": (det.start_line, det.end_line)})

    fn_old = [{"gt_id": gt.id, "filename": gt.filename, "gt_lines": (gt.start_line, gt.end_line)} for gt in remaining_old]
    fn_strict = [{"gt_id": gt.id, "filename": gt.filename, "gt_lines": (gt.start_line, gt.end_line)} for gt in remaining_strict]

    return (tp_old, fp_old, fn_old), (tp_strict, fp_strict, fn_strict)


# ──────────────────────────────────────────────────────────────
# Metriken & Ausgabe
# ──────────────────────────────────────────────────────────────
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
    print(f"{'Streng (IoU≥0.3)':<18} {ms['tp']:6} {ms['fp']:6} {ms['fn']:6} {ms['precision']:10.3f} {ms['recall']:10.3f} {ms['f1']:10.3f}")
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


def detect_category(filename: str) -> str:
    name = filename.lower()
    if name.startswith("opencode_"):
        rest = filename[len("opencode_"):] if filename.startswith("opencode_") else filename
        model_part = rest.split("_", 1)[0]
        if model_part.lower().startswith("grok"):
            model_part = "Grok" + model_part[4:]
        elif model_part.lower().startswith("gpt"):
            model_part = "GPT" + model_part[3:]
        return f"Opencode ({model_part})"
    if "grok" in name:
        return "Raw LLM (Grok)"
    elif re.search(r"gpt|openai|o1", name):
        return "Raw LLM (OpenAI)"
    return "Raw LLM (Unknown)"


def main():
    parser = argparse.ArgumentParser(description="LLM Code Review Evaluation – Dual Mode (Klassisch + Streng)")
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

    # Gesamtvergleich
    print("\n" + "═"*120)
    print(" GESAMTVERGLEICH – KLASSISCH vs. STRENG (IoU≥0.3 + Anti-Cheating) ".center(120))
    print("═"*120)
    print(f"{'Kategorie':<35} {'Typ':<12} {'Runs':>5} {'TP':>6} {'FP':>6} {'FN':>6} {'Prec':>8} {'Rec':>8} {'F1':>8}")
    print("─"*120)

    for cat in sorted(set(overall_classic.keys()) | set(overall_strict.keys())):
        mc = calculate_metrics(overall_classic[cat]["tp"], overall_classic[cat]["fp"], overall_classic[cat]["fn"])
        ms = calculate_metrics(overall_strict[cat]["tp"], overall_strict[cat]["fp"], overall_strict[cat]["fn"])
        runs = overall_classic[cat]["runs"]
        print(f"{cat:<35} {'Klassisch':<12} {runs:5} {mc['tp']:6} {mc['fp']:6} {mc['fn']:6} {mc['precision']:8.3f} {mc['recall']:8.3f} {mc['f1']:8.3f}")
        print(f"{'':<35} {'Streng':<12} {runs:5} {ms['tp']:6} {ms['fp']:6} {ms['fn']:6} {ms['precision']:8.3f} {ms['recall']:8.3f} {ms['f1']:8.3f}")
        print("─"*120)

    print(f"\nFertig! Alle Ergebnisse in: {output_dir}")


if __name__ == "__main__":
    main()