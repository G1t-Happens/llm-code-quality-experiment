#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import pandas as pd


@dataclass
class GroundTruthError:
    id: str                  # z. B. "E012"
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
    severity: str = "unknown"
    error_description: str = ""
    detected_id: str = "FP"   # "E012" oder "FP"


def extract_class_name(filename: str) -> str:
    return Path(filename).stem


# ----------------------------------------------------------------------
# 1. Ground Truth laden
# ----------------------------------------------------------------------
def load_ground_truth(csv_path: Path) -> List[GroundTruthError]:
    df = pd.read_csv(csv_path)
    required = {"id", "filename", "start_line", "end_line", "iso_category", "error_description", "severity"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Ground Truth fehlt Spalten: {missing}")

    errors = []
    for _, row in df.iterrows():
        errors.append(GroundTruthError(
            id=str(row["id"]).strip().upper(),
            filename=extract_class_name(row["filename"]),
            start_line=int(row["start_line"]),
            end_line=int(row["end_line"]),
            iso_category=str(row["iso_category"]),
            error_description=str(row["error_description"]),
            severity=str(row["severity"]),
            context_hash=str(row.get("context_hash", ""))
        ))
    return errors


# ----------------------------------------------------------------------
# 2. Detections laden – ID-Zuordnung statt semantically_correct_detected
# ----------------------------------------------------------------------
def load_verified_detections(csv_path: Path) -> List[DetectedError]:
    errors: List[DetectedError] = []
    try:
        df = pd.read_csv(csv_path)

        # Mögliche Spaltennamen für die ID-Zuordnung
        id_col = None
        candidates = ["detected_id", "ground_truth_id", "id_mapping", "mapped_id", "error_id",
                      "semantically_correct_detected", "correct_id"]
        for col in df.columns:
            if any(cand.lower() in col.lower() for cand in candidates):
                id_col = col
                break

        if id_col is None:
            print(f"Warnung: Keine ID-Spalte gefunden in {csv_path.name} → alle als FP")
            df["detected_id"] = "FP"
        else:
            df["detected_id"] = df[id_col].astype(str).str.strip().str.upper()
            # Alles, was nicht exakt wie E001, E123 usw. aussieht → FP
            df.loc[~df["detected_id"].str.fullmatch(r"E\d{3,}", na=True), "detected_id"] = "FP"

        valid_ids = (df["detected_id"] != "FP").sum()
        print(f"  → {len(df)} Zeilen geladen, davon {valid_ids} mit gültiger ID (E…)", end="")

        for _, row in df.iterrows():
            if not row.get("filename"):
                continue
            try:
                start = int(row["start_line"])
                end = int(row["end_line"])
            except (KeyError, ValueError, TypeError):
                continue

            errors.append(DetectedError(
                filename=extract_class_name(row["filename"]),
                start_line=start,
                end_line=end,
                severity="unknown",
                error_description=str(row.get("error_description", "")).strip(),
                detected_id=row["detected_id"]
            ))
    except Exception as e:
        print(f"Fehler beim Laden von {csv_path.name}: {e}")

    return errors


# ----------------------------------------------------------------------
# Hilfsfunktionen für Localization
# ----------------------------------------------------------------------
def lines_overlap(gt_start: int, gt_end: int, det_start: int, det_end: int, tol: int = 1) -> bool:
    return not ((gt_end + tol) < (det_start - tol) or (det_end + tol) < (gt_start - tol))


def calculate_iou(gt_start: int, gt_end: int, det_start: int, det_end: int) -> float:
    o_start = max(gt_start, det_start)
    o_end = min(gt_end, det_end)
    if o_start > o_end:
        return 0.0
    overlap = o_end - o_start + 1
    union = max(gt_end, det_end) - min(gt_start, det_start) + 1
    return overlap / union if union > 0 else 0.0


def strict_match(gt: GroundTruthError, det: DetectedError, tol: int = 3) -> bool:
    if gt.filename != det.filename:
        return False
    if not lines_overlap(gt.start_line, gt.end_line, det.start_line, det.end_line, tol):
        return False

    gts = gt.end_line - gt.start_line + 1
    ds = det.end_line - det.start_line + 1
    iou = calculate_iou(gt.start_line, gt.end_line, det.start_line, det.end_line)

    if gts == 1:
        return ds <= 7 and iou >= 0.15

    min_iou = max(0.2, 0.6 - 0.35 * math.log10(gts))
    max_det = min(gts * 5 + 15, gts * 3 + 60)
    center_dev = abs((gt.start_line + gt.end_line) / 2 - (det.start_line + det.end_line) / 2)
    max_shift = gts * 1.5 + 5

    return (iou >= min_iou and ds <= max_det and center_dev <= max_shift and ds >= 1)


# ----------------------------------------------------------------------
# 3. Fault Detection – rein ID-basiert
# ----------------------------------------------------------------------
def evaluate_fault_detection(gt_errors: List[GroundTruthError],
                             det_errors: List[DetectedError]) -> Tuple[list, list, list]:
    gt_ids = {gt.id for gt in gt_errors}

    tp_list, fp_list, fn_list = [], [], []

    detected_correct_ids = set()

    for det in det_errors:
        if det.detected_id in gt_ids:
            tp_list.append({
                "detected_id": det.detected_id,
                "filename": det.filename,
                "det_lines": (det.start_line, det.end_line),
                "error_description": det.error_description
            })
            detected_correct_ids.add(det.detected_id)
        else:
            fp_list.append({
                "filename": det.filename,
                "det_lines": (det.start_line, det.end_line),
                "error_description": det.error_description,
                "detected_id": det.detected_id
            })

    # FN = alle GT-IDs, die nicht erkannt wurden
    for gt in gt_errors:
        if gt.id not in detected_correct_ids:
            fn_list.append({
                "gt_id": gt.id,
                "filename": gt.filename,
                "gt_lines": (gt.start_line, gt.end_line),
                "error_description": gt.error_description
            })

    return tp_list, fp_list, fn_list


# ----------------------------------------------------------------------
# 4. Fault Localization – NUR auf semantisch korrekt erkannten Fehlern!
# ----------------------------------------------------------------------
def match_errors_localization(gt_errors: List[GroundTruthError],
                              det_errors: List[DetectedError],
                              tolerance: int = 1):
    # Nur Detections mit korrekter ID dürfen lokalisiert werden
    valid_dets = [d for d in det_errors if d.detected_id != "FP"]

    # GT nach Datei gruppieren
    gt_by_file = defaultdict(list)
    for gt in gt_errors:
        gt_by_file[gt.filename].append(gt)

    tp_classic, fp_classic, fn_classic = [], [], []
    tp_strict, fp_strict, fn_strict = [], [], []

    matched_gt_ids = set()

    for det in valid_dets:
        # Finde exakt den GT-Eintrag mit derselben ID
        gt_match = None
        for g in gt_by_file.get(det.filename, []):
            if g.id == det.detected_id:
                gt_match = g
                break
        if not gt_match:
            continue  # Sollte nie passieren

        classic_ok = lines_overlap(gt_match.start_line, gt_match.end_line,
                                   det.start_line, det.end_line, tolerance)
        strict_ok = strict_match(gt_match, det, tol=tolerance)

        entry = {
            "gt_id": gt_match.id,
            "filename": gt_match.filename,
            "gt_lines": (gt_match.start_line, gt_match.end_line),
            "det_lines": (det.start_line, det.end_line),
            "error_description": gt_match.error_description,
            "detected_id": det.detected_id
        }

        if classic_ok:
            tp_classic.append(entry)
            matched_gt_ids.add(gt_match.id)
            if strict_ok:
                tp_strict.append(entry)
            else:
                fp_strict.append({**entry, "note": "bad_localization"})
        else:
            fp_classic.append({**entry, "note": "bad_localization"})
            fp_strict.append({**entry, "note": "bad_localization"})

    # Alle Detections ohne korrekte ID → FP (für beide Metriken)
    for det in det_errors:
        if det.detected_id == "FP":
            fp_entry = {
                "filename": det.filename,
                "det_lines": (det.start_line, det.end_line),
                "error_description": det.error_description,
                "detected_id": "FP"
            }
            fp_classic.append(fp_entry)
            fp_strict.append(fp_entry)

    # FN = alle GT-Fehler, die nicht semantisch erkannt wurden
    for gt in gt_errors:
        if gt.id not in matched_gt_ids:
            fn_entry = {
                "gt_id": gt.id,
                "filename": gt.filename,
                "gt_lines": (gt.start_line, gt.end_line),
                "error_description": gt.error_description
            }
            fn_classic.append(fn_entry)
            fn_strict.append(fn_entry)

    return (tp_classic, fp_classic, fn_classic), (tp_strict, fp_strict, fn_strict)


# ----------------------------------------------------------------------
# Metriken & Ausgabe
# ----------------------------------------------------------------------
def calculate_metrics(tp: int, fp: int, fn: int) -> Dict[str, float]:
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f1}


def print_detection_report(category: str, tp_l: list, fp_l: list, fn_l: list):
    m = calculate_metrics(len(tp_l), len(fp_l), len(fn_l))
    print("\n" + "═" * 100)
    print(f" FAULT DETECTION (ID-basiert): {category} ".center(100))
    print("═" * 100)
    print(f"{'TP':>6} {'FP':>6} {'FN':>6} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print("─" * 100)
    print(f"{m['tp']:6} {m['fp']:6} {m['fn']:6} {m['precision']:10.3f} {m['recall']:10.3f} {m['f1']:10.3f}")
    print("═" * 100)


def print_localization_report(category: str, classic: tuple, strict: tuple, tol: int):
    (tp_c, fp_c, fn_c), (tp_s, fp_s, fn_s) = classic, strict
    mc = calculate_metrics(len(tp_c), len(fp_c), len(fn_c))
    ms = calculate_metrics(len(tp_s), len(fp_s), len(fn_s))
    print("\n" + "═" * 100)
    print(f" FAULT LOCALIZATION (nur nach korrekter Detection): {category} ".center(100))
    print("═" * 100)
    print(f"Toleranz: ±{tol} Zeilen")
    print(f"{'Methode':<18} {'TP':>6} {'FP':>6} {'FN':>6} {'Prec':>8} {'Rec':>8} {'F1':>10}")
    print("─" * 100)
    print(f"{'Classic (±1)':<18} {mc['tp']:6} {mc['fp']:6} {mc['fn']:6} {mc['precision']:8.3f} {mc['recall']:8.3f} {mc['f1']:10.3f}")
    print(f"{'Strict IoU':<18} {ms['tp']:6} {ms['fp']:6} {ms['fn']:6} {ms['precision']:8.3f} {ms['recall']:8.3f} {ms['f1']:10.3f}")
    print("═" * 100)


def save_detection_results(category: str, run_name: str, tp: list, fp: list, fn: list, out_dir: Path):
    safe = category.replace("(", "").replace(")", "").replace(" ", "_").replace("/", "_")
    run_dir = out_dir / safe / run_name / "fault_detection"
    run_dir.mkdir(parents=True, exist_ok=True)
    if tp: pd.DataFrame(tp).to_csv(run_dir / "tp.csv", index=False)
    if fp: pd.DataFrame(fp).to_csv(run_dir / "fp.csv", index=False)
    if fn: pd.DataFrame(fn).to_csv(run_dir / "fn.csv", index=False)
    (run_dir / "summary.json").write_text(json.dumps(calculate_metrics(len(tp), len(fp), len(fn)), indent=2))


def save_localization_results(category: str, run_name: str, classic: tuple, strict: tuple, out_dir: Path):
    safe = category.replace("(", "").replace(")", "").replace(" ", "_").replace("/", "_")
    run_dir = out_dir / safe / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    (tp_c, fp_c, fn_c), (tp_s, fp_s, fn_s) = classic, strict
    for data, name in [(tp_c, "tp_classic"), (fp_c, "fp_classic"), (fn_c, "fn_classic"),
                       (tp_s, "tp_strict"), (fp_s, "fp_strict"), (fn_s, "fn_strict")]:
        if data:
            pd.DataFrame(data).to_csv(run_dir / f"{name}.csv", index=False)

    summary = {
        "localization_classic": calculate_metrics(len(tp_c), len(fp_c), len(fn_c)),
        "localization_strict": calculate_metrics(len(tp_s), len(fp_s), len(fn_s))
    }
    (run_dir / "summary_localization.json").write_text(json.dumps(summary, indent=2))


def detect_category(path: Path) -> str:
    s = str(path)
    m = re.search(r"Detected[\/\\]([^\/\\]+)[\/\\].*?_fault_bugs_", s)
    if m:
        part = m.group(1)
        model = part.split("_")[-1]
        if "raw" in part.lower(): return f"Raw LLM ({model})"
        if "opencode" in part.lower(): return f"Opencode ({model})"
        if "finetuned" in part.lower(): return f"FineTuned ({model})"
        return f"{part} ({model})"
    return "Unknown"


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Hierarchische Evaluation: Detection → Localization")
    parser.add_argument("--experiment-dir", type=str, default="docs/experiment")
    parser.add_argument("--tolerance", type=int, default=1, help="Zeilentoleranz für Classic-Overlap")
    parser.add_argument("--gt-csv", type=str, default="ground_truth/seeded_errors_iso25010.csv")
    parser.add_argument("--model", type=str, help="Nur Modelle mit diesem Namen")
    args = parser.parse_args()

    base = Path(args.experiment_dir).resolve()
    gt_path = base / args.gt_csv
    if not gt_path.exists():
        raise FileNotFoundError(f"Ground Truth nicht gefunden: {gt_path}")

    gt_errors = load_ground_truth(gt_path)
    out_dir = base / "analysis"
    out_dir.mkdir(exist_ok=True)

    csv_files = sorted([p for p in base.rglob("detected_errors.csv")
                        if "_fault_bugs_" in str(p)])

    if not csv_files:
        raise FileNotFoundError("Keine detected_errors.csv gefunden!")

    print(f"{len(csv_files)} Runs gefunden.\n")

    # Aggregation
    agg_det = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "runs": 0})
    agg_loc_c = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "runs": 0})
    agg_loc_s = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "runs": 0})

    f1_det, f1_loc_c, f1_loc_s = {}, {}, {}

    for csv_file in csv_files:
        category = detect_category(csv_file)
        if args.model and args.model.lower() not in category.lower():
            continue

        run_name = csv_file.parent.name
        print(f"→ {run_name} | {category}")

        det_errors = load_verified_detections(csv_file)

        # 1. Fault Detection
        det_tp, det_fp, det_fn = evaluate_fault_detection(gt_errors, det_errors)
        print_detection_report(category, det_tp, det_fp, det_fn)
        save_detection_results(category, run_name, det_tp, det_fp, det_fn, out_dir)

        # 2. Fault Localization – nur auf korrekt erkannten
        loc_c, loc_s = match_errors_localization(gt_errors, det_errors, tolerance=args.tolerance)
        print_localization_report(category, loc_c, loc_s, args.tolerance)
        save_localization_results(category, run_name, loc_c, loc_s, out_dir)

        # Aggregation
        agg_det[category]["tp"] += len(det_tp)
        agg_det[category]["fp"] += len(det_fp)
        agg_det[category]["fn"] += len(det_fn)
        agg_det[category]["runs"] += 1

        agg_loc_c[category]["tp"] += len(loc_c[0])
        agg_loc_c[category]["fp"] += len(loc_c[1])
        agg_loc_c[category]["fn"] += len(loc_c[2])
        agg_loc_c[category]["runs"] += 1

        agg_loc_s[category]["tp"] += len(loc_s[0])
        agg_loc_s[category]["fp"] += len(loc_s[1])
        agg_loc_s[category]["fn"] += len(loc_s[2])
        agg_loc_s[category]["runs"] += 1

        f1_det.setdefault(category, []).append(calculate_metrics(len(det_tp), len(det_fp), len(det_fn))["f1"])
        f1_loc_c.setdefault(category, []).append(calculate_metrics(*map(len, loc_c))["f1"])
        f1_loc_s.setdefault(category, []).append(calculate_metrics(*map(len, loc_s))["f1"])

    # Finaler Gesamtbericht
    print("\n" + "═" * 160)
    print(" GESAMTVERGLEICH – HIERARCHISCH (Detection → Localization) ".center(160))
    print("═" * 160)
    print(f"{'Kategorie':<50} {'Typ':<28} {'Runs':>5} {'TP':>6} {'FP':>6} {'FN':>6} {'Prec':>8} {'Rec':>8} {'F1':>10} {'±σ':>8}")
    print("─" * 160)

    for cat in sorted(agg_det.keys()):
        runs = agg_det[cat]["runs"]

        md = calculate_metrics(agg_det[cat]["tp"], agg_det[cat]["fp"], agg_det[cat]["fn"])
        mc = calculate_metrics(agg_loc_c[cat]["tp"], agg_loc_c[cat]["fp"], agg_loc_c[cat]["fn"])
        ms = calculate_metrics(agg_loc_s[cat]["tp"], agg_loc_s[cat]["fp"], agg_loc_s[cat]["fn"])

        f1_d = mean(f1_det.get(cat, [0]))
        f1_c = mean(f1_loc_c.get(cat, [0]))
        f1_s = mean(f1_loc_s.get(cat, [0]))
        std_d = stdev(f1_det.get(cat, [])) if len(f1_det.get(cat, [])) > 1 else 0.0
        std_c = stdev(f1_loc_c.get(cat, [])) if len(f1_loc_c.get(cat, [])) > 1 else 0.0
        std_s = stdev(f1_loc_s.get(cat, [])) if len(f1_loc_s.get(cat, [])) > 1 else 0.0

        print(f"{cat:<50} {'Detection (ID)':<28} {runs:5} {md['tp']:6} {md['fp']:6} {md['fn']:6} {md['precision']:8.3f} {md['recall']:8.3f} {f1_d:10.3f} ±{std_d:6.3f}")
        print(f"{'':<50} {'Localization Classic':<28} {runs:5} {mc['tp']:6} {mc['fp']:6} {mc['fn']:6} {mc['precision']:8.3f} {mc['recall']:8.3f} {f1_c:10.3f} ±{std_c:6.3f}")
        print(f"{'':<50} {'Localization Strict IoU':<28} {runs:5} {ms['tp']:6} {ms['fp']:6} {ms['fn']:6} {ms['precision']:8.3f} {ms['recall']:8.3f} {f1_s:10.3f} ±{std_s:6.3f}")
        print("─" * 160)

    print(f"\nFertig! Alle Ergebnisse in: {out_dir}")
    print("   → fault_detection/ Ordner mit TP/FP/FN pro Run")
    print("   → Korrekte hierarchische Auswertung (Detection vor Localization)")


if __name__ == "__main__":
    main()