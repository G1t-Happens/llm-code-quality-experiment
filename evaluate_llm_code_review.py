# File: evaluate_llm_code_review.py
# 1:1-Matching mit Greedy-First-Match
# Erster Treffer → TP - Alle weiteren auf denselben Bug → FP
# Verhinder das Precision künstlich hochgepusht wird !!!

import pandas as pd
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
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


def lines_overlap(gt_start: int, gt_end: int, det_start: int, det_end: int, tolerance: int = 1) -> bool:
    return not ((gt_end + tolerance) < (det_start - tolerance) or
                (det_end + tolerance) < (gt_start - tolerance))


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


def load_llm_detections(json_path: Path) -> List[DetectedError]:
    """Sehr robustes Laden – übersteht kaputte JSONs, Strings, Markdown-Codeblöcke usw."""
    errors: List[DetectedError] = []

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        if not content:
            print(f"Warnung: {json_path.name} ist leer")
            return errors

        # Direkter JSON-Parse
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: erstes JSON-Objekt aus dem Text fischen (oft in ```json ... ```)
            match = re.search(r'(\[.*\]|{.*})', content, re.DOTALL)
            if not match:
                print(f"Fehler: Kann kein JSON in {json_path.name} finden")
                return errors
            data = json.loads(match.group(1))

        # Normalisierung auf Liste von Dicts
        if isinstance(data, dict):
            data = data.get("errors", [data])
        elif not isinstance(data, list):
            print(f"Warnung: Unerwarteter Datentyp in {json_path.name}: {type(data)}")
            return errors

        for item in data:
            if not isinstance(item, dict):
                continue

            filename = item.get("filename") or item.get("file") or item.get("path")
            if not filename:
                continue

            try:
                start_line = int(item["start_line"])
                end_line = int(item.get("end_line", start_line))
            except (KeyError, ValueError, TypeError):
                continue

            severity = str(item.get("severity", item.get("level", "unknown")))
            desc = str(item.get("error_description", item.get("description", item.get("message", "")))).strip()

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


def match_errors(gt_errors: List[GroundTruthError], det_errors: List[DetectedError], tolerance: int):
    tp, fp = [], []
    fn = gt_errors.copy()

    for det in det_errors:
        matched = False
        for i in range(len(fn) - 1, -1, -1):
            gt = fn[i]
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
                del fn[i]
                matched = True
                break
        if not matched:
            fp.append({
                "filename": det.filename,
                "det_lines": (det.start_line, det.end_line),
                "severity": det.severity,
                "description": det.error_description
            })

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


def calculate_metrics(tp: int, fp: int, fn: int) -> Dict[str, Any]:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def print_report(title: str, tp_list: List, fp_list: List, fn_list: List, tolerance: int):
    m = calculate_metrics(len(tp_list), len(fp_list), len(fn_list))
    print("\n" + "="*80)
    print(f" EVALUATION: {title.upper()} ".center(80))
    print("="*80)
    print(f"Toleranz: ±{tolerance} Zeilen")
    print(f"{'TP':>6} {'FP':>6} {'FN':>6}   Precision   Recall     F1")
    print(f"{m['tp']:6} {m['fp']:6} {m['fn']:6}   {m['precision']:8.3f}   {m['recall']:8.3f}   {m['f1']:8.3f}")
    print("="*80)


def save_run_results(model_name: str, run_name: str, tp, fp, fn, output_dir: Path):
    run_dir = output_dir / model_name.lower().replace(" ", "_") / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    if tp:
        pd.DataFrame(tp).to_csv(run_dir / "true_positives.csv", index=False)
    if fp:
        pd.DataFrame(fp).to_csv(run_dir / "false_positives.csv", index=False)
    if fn:
        pd.DataFrame(fn).to_csv(run_dir / "false_negatives.csv", index=False)

    summary = calculate_metrics(len(tp), len(fp), len(fn))
    summary["model"] = model_name
    summary["run"] = run_name
    with open(run_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


def detect_model_from_filename(filename: str) -> str:
    name = filename.lower()
    if "grok" in name:
        return "Grok"
    if re.search(r"openai|gpt|o1", name):
        return "OpenAI"
    if "claude" in name:
        return "Claude"
    if "gemini" in name:
        return "Gemini"
    if re.search(r"llama|meta", name):
        return "Llama"
    return "Unknown"


def main():
    parser = argparse.ArgumentParser(description="LLM Code Review Evaluation – nur saubere _fault_bugs_ Runs, mit per-Run-Analyse")
    parser.add_argument("--experiment-dir", type=str, default="docs/experiment",
                        help="Wurzelverzeichnis des Experiments")
    parser.add_argument("--tolerance", type=int, default=1, help="Zeilentoleranz (± Zeilen)")
    parser.add_argument("--gt-csv", type=str, default="ground_truth/seeded_errors_iso25010.csv",
                        help="Pfad zur Ground-Truth CSV")
    parser.add_argument("--model", type=str, choices=["grok", "openai", "claude", "gemini", "llama"],
                        help="Nur ein bestimmtes Modell auswerten")

    args = parser.parse_args()

    base_path = Path(args.experiment_dir).resolve()
    gt_path = base_path / args.gt_csv

    if not gt_path.exists():
        raise FileNotFoundError(f"Ground Truth nicht gefunden: {gt_path}")

    result_files = sorted(base_path.glob("results/*_fault_bugs_*.json"))

    if not result_files:
        raise FileNotFoundError("Keine *_fault_bugs_*.json Dateien in results/ gefunden!")

    gt_errors = load_ground_truth(gt_path)
    output_dir = base_path / "analysis"
    output_dir.mkdir(exist_ok=True)

    overall_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "runs": 0})

    print(f"Gefundene saubere LLM-Runs: {len(result_files)}\n")

    for json_file in result_files:
        model_name = detect_model_from_filename(json_file.name)

        if args.model and args.model.lower() != model_name.lower():
            continue

        run_name = json_file.stem

        print(f"→ {json_file.name} → {model_name}")

        det_errors = load_llm_detections(json_file)
        tp, fp, fn_list = match_errors(gt_errors, det_errors, tolerance=args.tolerance)

        title = f"{model_name} – {run_name}"
        print_report(title, tp, fp, fn_list, args.tolerance)

        save_run_results(model_name, run_name, tp, fp, fn_list, output_dir)

        overall_stats[model_name]["tp"] += len(tp)
        overall_stats[model_name]["fp"] += len(fp)
        overall_stats[model_name]["fn"] += len(fn_list)
        overall_stats[model_name]["runs"] += 1

    # Gesamtvergleich
    print("\n" + "═"*100)
    print("                       GESAMTVERGLEICH NACH MODELL")
    print("═"*100)
    print(f"{'Modell':<12} {'Runs':>5} {'TP':>6} {'FP':>6} {'FN':>6} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print("─"*100)

    comparison = []
    for model, stats in overall_stats.items():
        m = calculate_metrics(stats["tp"], stats["fp"], stats["fn"])
        print(f"{model:<12} {stats['runs']:5} {stats['tp']:6} {stats['fp']:6} {stats['fn']:6} "
              f"{m['precision']:10.3f} {m['recall']:10.3f} {m['f1']:10.3f}")
        comparison.append({"model": model, "runs": stats["runs"], **m})

    if comparison:
        df = pd.DataFrame(comparison).sort_values("f1", ascending=False)
        df.to_csv(output_dir / "model_comparison.csv", index=False)
        try:
            df.to_markdown(output_dir / "model_comparison.md", index=False)
        except:
            pass  # to_markdown kann bei manchen pandas-Versionen fehlen
        print(f"\nSieger: {df.iloc[0]['model']} mit F1 = {df.iloc[0]['f1']:.3f}")

    print(f"\nFertig! Ergebnisse in: {output_dir}")
    print("   └─ pro Modell → pro Run → true_positives.csv / false_positives.csv / false_negatives.csv / summary.json")


if __name__ == "__main__":
    main()