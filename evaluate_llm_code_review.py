# File: analysis/evaluate_llm_code_review.py
import pandas as pd
import json
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import argparse

@dataclass
class GroundTruthError:
    id: str
    filename: str
    start_line: int
    end_line: int
    iso_category: str
    error_description: str
    severity: str
    context_hash: str

@dataclass
class DetectedError:
    filename: str
    start_line: int
    end_line: int
    severity: str
    error_description: str

def extract_class_name(filename: str) -> str:
    """Extrahiert nur den Klassennamen aus einem Dateipfad"""
    return Path(filename).name

def lines_overlap(gt_start: int, gt_end: int, det_start: int, det_end: int, tolerance: int = 1) -> bool:
    """
    Prüft, ob sich zwei Code-Bereiche mit Toleranz überschneiden.
    Ein Fehler gilt als erkannt, wenn der erkannte Bereich innerhalb von ±tolerance Zeilen liegt
    ODER sich die Intervalle überschneiden.
    """
    # Erweiterte Intervalle mit Toleranz
    gt_exp_start = gt_start - tolerance
    gt_exp_end = gt_end + tolerance
    det_exp_start = det_start - tolerance
    det_exp_end = det_end + tolerance

    return not (gt_exp_end < det_exp_start or det_exp_end < gt_exp_start)

def load_ground_truth(csv_path: str) -> List[GroundTruthError]:
    df = pd.read_csv(csv_path)
    required_cols = ["id", "filename", "start_line", "end_line", "iso_category", "error_description", "severity"]
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"CSV fehlt Spalten: {set(required_cols) - set(df.columns)}")

    errors = []
    for _, row in df.iterrows():
        errors.append(GroundTruthError(
            id=str(row["id"]),
            filename=extract_class_name(row["filename"]),
            start_line=int(row["start_line"]),
            end_line=int(row["end_line"]),
            iso_category=str(row["iso_category"]),
            error_description=str(row["error_description"]),
            severity=str(row["severity"]),
            context_hash=str(row.get("context_hash", ""))
        ))
    return errors

def load_llm_detections(json_path: str) -> List[DetectedError]:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    errors = []
    for item in data:
        # Robust gegen leicht unterschiedliche Formate
        filename = item.get("filename") or item.get("file")
        if not filename:
            continue
        start_line = int(item["start_line"])
        end_line = int(item.get("end_line", start_line))  # fallback auf start = end
        severity = str(item.get("severity", "unknown"))
        desc = str(item.get("error_description", item.get("description", "")))

        errors.append(DetectedError(
            filename=extract_class_name(filename),
            start_line=start_line,
            end_line=end_line,
            severity=severity,
            error_description=desc
        ))
    return errors

def match_errors(gt_errors: List[GroundTruthError], det_errors: List[DetectedError], tolerance: int = 1):
    tp = []
    fp = []
    fn = list(gt_errors)  # alle anfangs als unverkannt

    used_det_indices = set()

    for i, det in enumerate(det_errors):
        matched = False
        for j, gt in enumerate(fn):
            if (gt.filename == det.filename and
                    lines_overlap(gt.start_line, gt.end_line, det.start_line, det.end_line, tolerance)):
                tp.append({
                    "gt_id": gt.id,
                    "filename": gt.filename,
                    "gt_lines": (gt.start_line, gt.end_line),
                    "det_lines": (det.start_line, det.end_line),
                    "severity_gt": gt.severity,
                    "severity_det": det.severity,
                    "gt_description": gt.error_description,
                    "det_description": det.error_description
                })
                del fn[j]  # entferne aus unverkannten
                used_det_indices.add(i)
                matched = True
                break

        if not matched:
            fp.append({
                "filename": det.filename,
                "det_lines": (det.start_line, det.end_line),
                "severity": det.severity,
                "description": det.error_description
            })

    # Alle verbleibenden GT sind False Negatives
    fn_list = [
        {
            "gt_id": gt.id,
            "filename": gt.filename,
            "gt_lines": (gt.start_line, gt.end_line),
            "severity": gt.severity,
            "description": gt.error_description
        } for gt in fn
    ]

    return tp, fp, fn_list

def print_report(tp: List, fp: List, fn: List, tolerance: int):
    print("="*60)
    print("           CODE REVIEW LLM EVALUATION REPORT")
    print("="*60)
    print(f"Toleranz: ±{tolerance} Zeilen")
    print(f"True Positives (TP):  {len(tp)}")
    print(f"False Positives (FP): {len(fp)}")
    print(f"False Negatives (FN): {len(fn)}")
    print("-"*60)

    precision = len(tp) / (len(tp) + len(fp)) if (len(tp) + len(fp)) > 0 else 0
    recall = len(tp) / (len(tp) + len(fn)) if (len(tp) + len(fn)) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    print(f"Precision: {precision:.3f}")
    print(f"Recall:    {recall:.3f}")
    print(f"F1-Score:  {f1:.3f}")
    print("="*60)

    if tp:
        print("\nTRUE POSITIVES:")
        for m in tp:
            print(f"  ✓ {m['gt_id']:>4} | {m['filename']:<20} | "
                  f"GT: {m['gt_lines']} → DET: {m['det_lines']}")

    if fp:
        print("\nFALSE POSITIVES (Halluzinationen / Übererkennung):")
        for m in fp:
            print(f"  ✗      | {m['filename']:<20} | "
                  f"Lines: {m['det_lines']} | {m['severity']} | {m['description'][:80]}...")

    if fn:
        print("\nFALSE NEGATIVES (Übersehene echte Fehler):")
        for m in fn:
            print(f"  − {m['gt_id']:>4} | {m['filename']:<20} | "
                  f"Lines: {m['gt_lines']} | {m['severity']} | {m['description'][:80]}...")

def save_detailed_results(tp, fp, fn, output_dir: str):
    Path(output_dir).mkdir(exist_ok=True)

    pd.DataFrame(tp).to_csv(f"{output_dir}/true_positives.csv", index=False)
    pd.DataFrame(fp).to_csv(f"{output_dir}/false_positives.csv", index=False)
    pd.DataFrame(fn).to_csv(f"{output_dir}/false_negatives.csv", index=False)

    summary = {
        "true_positives": len(tp),
        "false_positives": len(fp),
        "false_negatives": len(fn),
        "precision": len(tp) / (len(tp) + len(fp)) if (len(tp) + len(fp)) > 0 else 0,
        "recall": len(tp) / (len(tp) + len(fn)) if (len(tp) + len(fn)) > 0 else 0,
        "f1": 2 * (len(tp) / (len(tp) + len(fp))) * (len(tp) / (len(tp) + len(fn))) /
              ((len(tp) / (len(tp) + len(fp))) + (len(tp) / (len(tp) + len(fn)))) if (len(tp) + len(fp) + len(fn)) > 0 else 0
    }
    with open(f"{output_dir}/summary.json", "w") as f:
        json.dump(summary, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Wissenschaftliche Auswertung von LLM Code Reviews")
    parser.add_argument("--experiment-dir", type=str, default="docs/experiment", help="Wurzelverzeichnis des Experiments")
    parser.add_argument("--tolerance", type=int, default=1,help="Zeilentoleranz für Matching (±Zeilen)")
    parser.add_argument("--gt-csv", type=str, default="ground_truth/seeded_errors_iso25010.csv")
    parser.add_argument("--results-glob", type=str, default="results/faults_detected_*.json")

    args = parser.parse_args()

    base_path = Path(args.experiment_dir)

    gt_path = base_path / args.gt_csv
    if not gt_path.exists():
        raise FileNotFoundError(f"Ground Truth nicht gefunden: {gt_path}")

    result_files = list(base_path.glob(args.results_glob))
    if not result_files:
        raise FileNotFoundError(f"Keine LLM-JSON-Datei gefunden mit Pattern: {args.results_glob}")

    print(f"Found {len(result_files)} LLM result file(s)\n")

    all_tp, all_fp, all_fn = [], [], []

    for json_file in result_files:
        print(f"Analysiere: {json_file.name}")
        gt_errors = load_ground_truth(gt_path)
        det_errors = load_llm_detections(json_file)

        tp, fp, fn = match_errors(gt_errors, det_errors, tolerance=args.tolerance)

        all_tp.extend(tp)
        all_fp.extend(fp)
        all_fn.extend(fn)

        # Pro-Datei Report
        print_report(tp, fp, fn, args.tolerance)
        print("\n" + "─"*60 + "\n")

    # Gesamtbericht
    print("GESAMTERGEBNIS ÜBER ALLE RUNS")
    print_report(all_tp, all_fp, all_fn, args.tolerance)

    # Speichern
    output_dir = base_path / "analysis"
    save_detailed_results(all_tp, all_fp, all_fn, output_dir)
    print(f"\nDetaillierte Ergebnisse gespeichert in: {output_dir}/")

if __name__ == "__main__":
    main()