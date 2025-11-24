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

    fn_list = [{"gt_id": gt.id, "filename": gt.filename, "gt_lines": (gt.start_line, gt.end_line),
                "severity": gt.severity, "description": gt.error_description} for gt in fn]
    return tp, fp, fn_list


def calculate_metrics(tp: int, fp: int, fn: int) -> Dict[str, Any]:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def print_report(title: str, tp_list: List, fp_list: List, fn_list: List, tolerance: int):
    m = calculate_metrics(len(tp_list), len(fp_list), len(fn_list))
    print("\n" + "═"*92)
    print(f" EVALUATION: {title.upper()} ".center(92))
    print("═"*92)
    print(f"Toleranz: ±{tolerance} Zeilen")
    print(f"{'TP':>6} {'FP':>6} {'FN':>6}   Precision   Recall     F1")
    print(f"{m['tp']:6} {m['fp']:6} {m['fn']:6}   {m['precision']:8.3f}   {m['recall']:8.3f}   {m['f1']:8.3f}")
    print("═"*92)


def save_run_results(category: str, run_name: str, tp, fp, fn, output_dir: Path):
    safe_category = category.replace("(", "").replace(")", "").replace(" ", "_")
    run_dir = output_dir / safe_category / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    if tp: pd.DataFrame(tp).to_csv(run_dir / "true_positives.csv", index=False)
    if fp: pd.DataFrame(fp).to_csv(run_dir / "false_positives.csv", index=False)
    if fn: pd.DataFrame(fn).to_csv(run_dir / "false_negatives.csv", index=False)
    summary = calculate_metrics(len(tp), len(fp), len(fn))
    summary["category"] = category
    summary["run"] = run_name
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def detect_category(filename: str) -> str:
    name = filename.lower()

    if name.startswith("opencode_"):
        rest = filename[len("opencode_"):] if filename.startswith("opencode_") else filename
        model_part = rest.split("_", 1)[0]

        if model_part.lower().startswith("grok"):
            model_part = "Grok" + model_part[4:]
        elif model_part.lower().startswith("gpt"):
            model_part = "GPT" + model_part[3:]
        elif "o1" in model_part.lower():
            model_part = "o1" + model_part[2:] if not model_part.lower().startswith("o1") else model_part
        else:
            model_part = model_part.replace("-", " ").title()

        return f"Opencode ({model_part})"

    if "grok" in name:
        return "Raw LLM (Grok)"
    elif re.search(r"gpt|openai|o1", name):
        return "Raw LLM (OpenAI)"
    else:
        return "Raw LLM (Unknown)"


def main():
    parser = argparse.ArgumentParser(description="LLM Code Review Evaluation")
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

    overall_stats = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "runs": 0})

    print(f"Gefundene Runs: {len(result_files)}\n")

    for json_file in result_files:
        category = detect_category(json_file.name)

        if args.model and args.model.lower() not in category.lower():
            continue

        run_name = json_file.stem
        print(f"→ {json_file.name}  →  {category}")

        det_errors = load_llm_detections(json_file)
        tp, fp, fn_list = match_errors(gt_errors, det_errors, tolerance=args.tolerance)

        print_report(category, tp, fp, fn_list, args.tolerance)
        save_run_results(category, run_name, tp, fp, fn_list, output_dir)

        overall_stats[category]["tp"] += len(tp)
        overall_stats[category]["fp"] += len(fp)
        overall_stats[category]["fn"] += len(fn_list)
        overall_stats[category]["runs"] += 1

    print("\n" + "═"*100)
    print("                GESAMTVERGLEICH: AGENT + MODELL")
    print("═"*100)
    print(f"{'Kategorie':<35} {'Runs':>5} {'TP':>6} {'FP':>6} {'FN':>6} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print("─"*100)

    for cat, stats in sorted(overall_stats.items()):
        m = calculate_metrics(stats["tp"], stats["fp"], stats["fn"])
        print(f"{cat:<35} {stats['runs']:5} {stats['tp']:6} {stats['fp']:6} {stats['fn']:6} "
              f"{m['precision']:10.3f} {m['recall']:10.3f} {m['f1']:10.3f}")

    if overall_stats:
        df = pd.DataFrame([
            {"category": cat, "runs": s["runs"], **calculate_metrics(s["tp"], s["fp"], s["fn"])}
            for cat, s in overall_stats.items()
        ]).sort_values("f1", ascending=False)
        df.to_csv(output_dir / "comparison_agent_model.csv", index=False)
        print(f"\nSieger: {df.iloc[0]['category']} mit F1 = {df.iloc[0]['f1']:.3f}")

    print(f"\nFertig! Alle Ergebnisse in: {output_dir}")


if __name__ == "__main__":
    main()