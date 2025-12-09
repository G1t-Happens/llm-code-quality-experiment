#!/usr/bin/env python3
import argparse
import json
import math
import re
import pandas as pd
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple



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

        id_col = None
        candidates = ["detected_id", "ground_truth_id", "id_mapping", "mapped_id", "error_id",
                      "semantically_correct_detected", "correct_id", "id"]
        for col in df.columns:
            if any(cand.lower() in col.lower() for cand in candidates):
                id_col = col
                break

        if id_col is None:
            print(f"Warnung: Keine ID-Spalte in {csv_path.name} → alle FP")
            df["detected_id"] = "FP"
        else:
            df["detected_id"] = df[id_col].astype(str).str.strip().str.upper()
            df.loc[~df["detected_id"].str.fullmatch(r"E\d{3,}", na=True), "detected_id"] = "FP"

        valid = (df["detected_id"] != "FP").sum()
        print(f"  → {len(df)} Zeilen, {valid} mit gültiger ID")

        for _, row in df.iterrows():
            if not row.get("filename"):
                continue
            try:
                start = int(row["start_line"])
                end = int(row["end_line"])
            except:
                continue

            errors.append(DetectedError(
                filename=extract_class_name(row["filename"]),
                start_line=start,
                end_line=end,
                error_description=str(row.get("error_description", "")).strip(),
                detected_id=row["detected_id"]
            ))
    except Exception as e:
        print(f"Fehler: {e}")
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
def evaluate_fault_detection(gt_errors: List[GroundTruthError], det_errors: List[DetectedError]):
    gt_ids = {gt.id for gt in gt_errors}

    # Zähle wie oft jede ID detektiert wurde
    detection_count = defaultdict(int)
    for det in det_errors:
        if det.detected_id != "FP":
            detection_count[det.detected_id] += 1

    tp_list, fp_list, fn_list = [], [], []
    used_gt_ids = set()

    for det in det_errors:
        if det.detected_id == "FP" or det.detected_id not in gt_ids:
            fp_list.append({
                "filename": det.filename,
                "det_lines": (det.start_line, det.end_line),
                "error_description": det.error_description,
                "detected_id": det.detected_id if det.detected_id != "FP" else "FP"
            })
        else:
            # Nur der erste Treffer pro ID ist TP → alle weiteren sind FP
            if det.detected_id not in used_gt_ids and detection_count[det.detected_id] >= 1:
                tp_list.append({
                    "detected_id": det.detected_id,
                    "filename": det.filename,
                    "det_lines": (det.start_line, det.end_line),
                    "error_description": det.error_description
                })
                used_gt_ids.add(det.detected_id)
            else:
                fp_list.append({
                    "filename": det.filename,
                    "det_lines": (det.start_line, det.end_line),
                    "error_description": det.error_description,
                    "detected_id": det.detected_id,
                    "note": "duplicate_detection"
                })

    # FN
    for gt in gt_errors:
        if gt.id not in used_gt_ids:
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
def match_errors_localization(gt_errors: List[GroundTruthError], det_errors: List[DetectedError], tolerance: int = 1):
    # Nur Detections mit gültiger ID
    valid_dets = [d for d in det_errors if d.detected_id != "FP"]

    # GT nach Datei + ID für schnellen Zugriff
    gt_lookup: Dict[str, GroundTruthError] = {}
    for gt in gt_errors:
        key = (gt.filename, gt.id)
        gt_lookup[key] = gt

    tp_classic, fp_classic, fn_classic = [], [], []
    tp_strict, fp_strict, fn_strict = [], [], []

    matched_gt_keys = set()  # (filename, id)

    # Zuerst: nur eine Detection pro GT-ID darf matchen
    seen_ids_per_file = defaultdict(int)

    for det in valid_dets:
        key = (det.filename, det.detected_id)
        if key in gt_lookup and key not in matched_gt_keys:
            gt = gt_lookup[key]

            classic_ok = lines_overlap(gt.start_line, gt.end_line, det.start_line, det.end_line, tolerance)
            strict_ok = strict_match(gt, det, tol=tolerance)

            entry = {
                "gt_id": gt.id,
                "filename": gt.filename,
                "gt_lines": (gt.start_line, gt.end_line),
                "det_lines": (det.start_line, det.end_line),
                "error_description": gt.error_description,
                "detected_id": det.detected_id
            }

            if classic_ok:
                tp_classic.append(entry)
                matched_gt_keys.add(key)
                if strict_ok:
                    tp_strict.append(entry)
                else:
                    fp_strict.append({**entry, "note": "bad_localization"})
            else:
                fp_classic.append({**entry, "note": "bad_localization"})
                fp_strict.append({**entry, "note": "bad_localization"})
        else:
            # Duplikat oder falsche ID → FP
            fp_classic.append({
                "filename": det.filename,
                "det_lines": (det.start_line, det.end_line),
                "error_description": det.error_description,
                "detected_id": det.detected_id,
                "note": "duplicate_or_wrong_id"
            })
            fp_strict.append({
                "filename": det.filename,
                "det_lines": (det.start_line, det.end_line),
                "error_description": det.error_description,
                "detected_id": det.detected_id,
                "note": "duplicate_or_wrong_id"
            })

    # Alle FP-Detections (keine ID)
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

    # FN = nicht erkannte GT-IDs
    for gt in gt_errors:
        key = (gt.filename, gt.id)
        if key not in matched_gt_keys:
            fn_entry = {
                "gt_id": gt.id,
                "filename": gt.filename,
                "gt_lines": (gt.start_line, gt.end_line),
                "error_description": gt.error_description
            }
            fn_classic.append(fn_entry)
            fn_strict.append(fn_entry)

    return (tp_classic, fp_classic, fn_classic), (tp_strict, fp_strict, fn_strict)


# Fault Localization – IoU mit mehreren Thresholds (0.25, 0.50, 0.75)
def adaptive_iou_threshold(gt_lines: int) -> float:
    """Smooth adaptiver Mindest-IoU basierend auf GT-Größe"""
    if gt_lines <= 1:
        return 0.85
    return max(0.30, 1.00 - 0.28 * math.log10(gt_lines))


def match_errors_adaptive_smooth_iou(
        gt_errors: List[Any],
        det_errors: List[Any],
        report_thresholds: List[float] = None
) -> Dict[str, Tuple[List[dict], List[dict], List[dict]]]:
    """
    State-of-the-art adaptive IoU matching with fair thresholds + classic reporting.
    Returns both fixed IoU thresholds AND true adaptive matching.
    """
    if report_thresholds is None:
        report_thresholds = [0.25, 0.50, 0.75]
    report_thresholds = sorted(set(report_thresholds))

    # Results for fixed thresholds
    fixed_results = {th: {"tp": [], "fp": [], "fn": []} for th in report_thresholds}
    # True adaptive results
    adaptive_tp, adaptive_fp, adaptive_fn = [], [], []

    # Group by file
    gt_by_file = defaultdict(list)
    det_by_file = defaultdict(list)
    for gt in gt_errors:
        gt_by_file[gt.filename].append(gt)
    for det in det_errors:
        det_by_file[det.filename].append(det)

    globally_matched_gt = set()  # (filename, gt.id)

    for filename in set(gt_by_file) | set(det_by_file):
        current_gts = gt_by_file[filename]
        current_dets = det_by_file.get(filename, [])

        # GT lookup by ID
        gt_lookup = {gt.id: gt for gt in current_gts}

        # Only detections with valid ID
        candidates = [d for d in current_dets if d.detected_id != "FP"]
        marked_fps = [d for d in current_dets if d.detected_id == "FP"]

        # --- Collect possible (det, gt) pairs ---
        pairs = []
        for det in candidates:
            gt_id = det.detected_id
            if gt_id not in gt_lookup:
                continue
            gt = gt_lookup[gt_id]
            key = (filename, gt_id)
            if key in globally_matched_gt:
                continue
            iou = calculate_iou(gt.start_line, gt.end_line, det.start_line, det.end_line)
            pairs.append((iou, det, gt, key))

        # --- Greedy matching: best IoU first ---
        pairs.sort(reverse=True, key=lambda x: x[0])

        used_dets = set()

        for iou, det, gt, key in pairs:
            if key in globally_matched_gt or id(det) in used_dets:
                continue

            gt_lines = gt.end_line - gt.start_line + 1
            required_iou = adaptive_iou_threshold(gt_lines)
            is_adaptive_tp = iou >= required_iou

            entry = {
                "filename": filename,
                "gt_id": gt.id,
                "gt_lines": (gt.start_line, gt.end_line),
                "det_lines": (det.start_line, det.end_line),
                "iou": round(iou, 4),
                "required_iou": round(required_iou, 3),
                "adaptive_tp": is_adaptive_tp,
                "gt_size": gt_lines,
                "error_description": gt.error_description
            }

            # Adaptive decision (the real one!)
            if is_adaptive_tp:
                adaptive_tp.append(entry)
            else:
                adaptive_fp.append({**entry, "note": f"IoU {iou:.3f} < required {required_iou:.3f}"})

            # Fixed threshold reporting (for comparison)
            for th in report_thresholds:
                if iou >= th:
                    fixed_results[th]["tp"].append(entry.copy())
                else:
                    fixed_results[th]["fp"].append({**entry, "note": f"IoU {iou:.3f} < {th}"})

            globally_matched_gt.add(key)
            used_dets.add(id(det))

        # --- Unmatched candidates → FP ---
        for det in candidates:
            if id(det) in used_dets:
                continue
            reason = "wrong_id" if det.detected_id not in gt_lookup else "low_iou_duplicate"
            fp_entry = {
                "filename": filename,
                "detected_id": det.detected_id,
                "det_lines": (det.start_line, det.end_line),
                "note": reason
            }
            adaptive_fp.append(fp_entry)
            for th in report_thresholds:
                fixed_results[th]["fp"].append(fp_entry.copy())

        # --- Marked as FP ---
        for det in marked_fps:
            fp_entry = {
                "filename": filename,
                "det_lines": (det.start_line, det.end_line),
                "detected_id": "FP",
                "note": "marked_as_fp"
            }
            adaptive_fp.append(fp_entry)
            for th in report_thresholds:
                fixed_results[th]["fp"].append(fp_entry.copy())

        # --- False Negatives ---
        for gt in current_gts:
            key = (filename, gt.id)
            if key not in globally_matched_gt:
                fn_entry = {
                    "filename": filename,
                    "gt_id": gt.id,
                    "gt_lines": (gt.start_line, gt.end_line),
                    "required_iou": round(adaptive_iou_threshold(gt.end_line - gt.start_line + 1), 3),
                    "error_description": gt.error_description
                }
                adaptive_fn.append(fn_entry)
                for th in report_thresholds:
                    fixed_results[th]["fn"].append(fn_entry.copy())

    # Build final result dict
    result = {
        "fixed_0.25": (fixed_results[0.25]["tp"], fixed_results[0.25]["fp"], fixed_results[0.25]["fn"]),
        "fixed_0.50": (fixed_results[0.50]["tp"], fixed_results[0.50]["fp"], fixed_results[0.50]["fn"]),
        "fixed_0.75": (fixed_results[0.75]["tp"], fixed_results[0.75]["fp"], fixed_results[0.75]["fn"]),
        "adaptive": (adaptive_tp, adaptive_fp, adaptive_fn),
    }

    # Optional debug print
    if adaptive_tp or adaptive_fp:
        avg_req = mean(entry.get("required_iou", 0.5) for entry in adaptive_tp + adaptive_fp if "required_iou" in entry)
        print(f"   → Adaptives IoU: Ø benötigter IoU = {avg_req:.3f} (über {len(adaptive_tp)+len(adaptive_fp)} Zuordnungen)")

    return result

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


def print_localization_report(category: str, classic: tuple, strict: tuple, iou_results: dict, tol: int):
    (tp_c, fp_c, fn_c), (tp_s, fp_s, fn_s) = classic, strict
    mc = calculate_metrics(len(tp_c), len(fp_c), len(fn_c))
    ms = calculate_metrics(len(tp_s), len(fp_s), len(fn_s))

    print("\n" + "═" * 100)
    print(f" FAULT LOCALIZATION (nur nach korrekter Detection): {category} ".center(100))
    print("═" * 100)
    print(f"Toleranz Classic: ±{tol} Zeilen")
    print(f"{'Methode':<22} {'TP':>6} {'FP':>6} {'FN':>6} {'Prec':>8} {'Rec':>8} {'F1':>10}")
    print("─" * 100)
    print(f"{'Classic (Overlap)':<22} {mc['tp']:6} {mc['fp']:6} {mc['fn']:6} {mc['precision']:8.3f} {mc['recall']:8.3f} {mc['f1']:10.3f}")
    print(f"{'Strict (dynam. IoU)':<22} {ms['tp']:6} {ms['fp']:6} {ms['fn']:6} {ms['precision']:8.3f} {ms['recall']:8.3f} {ms['f1']:10.3f}")

    print(f"{'─' * 20:<22} {'─' * 6} {'─' * 6} {'─' * 6} {'─' * 8} {'─' * 8} {'─' * 10}")

    # ─── Die drei alten (fixen) IoU-Zeilen ───
    print(f"{'IoU ≥ 0.25':<22} {len(iou_results['fixed_0.25'][0]):6} {len(iou_results['fixed_0.25'][1]):6} {len(iou_results['fixed_0.25'][2]):6} "
          f"{calculate_metrics(*map(len, iou_results['fixed_0.25']))['precision']:8.3f} "
          f"{calculate_metrics(*map(len, iou_results['fixed_0.25']))['recall']:8.3f} "
          f"{calculate_metrics(*map(len, iou_results['fixed_0.25']))['f1']:10.3f}")
    print(f"{'IoU ≥ 0.50':<22} {len(iou_results['fixed_0.50'][0]):6} {len(iou_results['fixed_0.50'][1]):6} {len(iou_results['fixed_0.50'][2]):6} "
          f"{calculate_metrics(*map(len, iou_results['fixed_0.50']))['precision']:8.3f} "
          f"{calculate_metrics(*map(len, iou_results['fixed_0.50']))['recall']:8.3f} "
          f"{calculate_metrics(*map(len, iou_results['fixed_0.50']))['f1']:10.3f}")
    print(f"{'IoU ≥ 0.75':<22} {len(iou_results['fixed_0.75'][0]):6} {len(iou_results['fixed_0.75'][1]):6} {len(iou_results['fixed_0.75'][2]):6} "
          f"{calculate_metrics(*map(len, iou_results['fixed_0.75']))['precision']:8.3f} "
          f"{calculate_metrics(*map(len, iou_results['fixed_0.75']))['recall']:8.3f} "
          f"{calculate_metrics(*map(len, iou_results['fixed_0.75']))['f1']:10.3f}")

    # ─── HIER KOMMT DIE NEUE ADAPTIVE ZEILE ───
    if "adaptive" in iou_results:
        tp, fp, fn = iou_results["adaptive"]
        m = calculate_metrics(len(tp), len(fp), len(fn))
        print(f"{'IoU ≥ adaptive (fair!)':<22} {len(tp):6} {len(fp):6} {len(fn):6} "
              f"{m['precision']:8.3f} {m['recall']:8.3f} {m['f1']:10.3f}  ← NEW BEST!")

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

def save_iou_localization_results(category: str, run_name: str, iou_results: dict, out_dir: Path):
    safe = category.replace("(", "").replace(")", "").replace(" ", "_").replace("/", "_")
    run_dir = out_dir / safe / run_name / "localization_iou"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Nur die fixen Thresholds speichern (adaptive hat keinen numerischen Key)
    fixed_keys = ["fixed_0.25", "fixed_0.50", "fixed_0.75"]
    for key in fixed_keys:
        if key not in iou_results:
            continue
        tp, fp, fn = iou_results[key]
        th_str = key.replace("fixed_", "").replace(".", "")
        if tp: pd.DataFrame(tp).to_csv(run_dir / f"tp_iou_{th_str}.csv", index=False)
        if fp: pd.DataFrame(fp).to_csv(run_dir / f"fp_iou_{th_str}.csv", index=False)
        if fn: pd.DataFrame(fn).to_csv(run_dir / f"fn_iou_{th_str}.csv", index=False)

    # Adaptive separat speichern (schöner Name)
    if "adaptive" in iou_results:
        tp, fp, fn = iou_results["adaptive"]
        if tp: pd.DataFrame(tp).to_csv(run_dir / "tp_adaptive.csv", index=False)
        if fp: pd.DataFrame(fp).to_csv(run_dir / "fp_adaptive.csv", index=False)
        if fn: pd.DataFrame(fn).to_csv(run_dir / "fn_adaptive.csv", index=False)

    # Summary nur für fixe Thresholds + adaptive
    summary = {}
    for key in fixed_keys:
        if key in iou_results:
            tp, fp, fn = iou_results[key]
            th = float(key.split("_")[-1])
            summary[f"iou_{th:.2f}"] = calculate_metrics(len(tp), len(fp), len(fn))
    if "adaptive" in iou_results:
        tp, fp, fn = iou_results["adaptive"]
        summary["adaptive"] = calculate_metrics(len(tp), len(fp), len(fn))

    (run_dir / "summary_iou.json").write_text(json.dumps(summary, indent=2))


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

    agg_iou = defaultdict(lambda: {
        0.25: {"tp": 0, "fp": 0, "fn": 0, "runs": 0},
        0.50: {"tp": 0, "fp": 0, "fn": 0, "runs": 0},
        0.75: {"tp": 0, "fp": 0, "fn": 0, "runs": 0}
    })
    f1_iou = defaultdict(lambda: {0.25: [], 0.50: [], 0.75: []})

    f1_det = defaultdict(list)
    f1_loc_c = defaultdict(list)
    f1_loc_s = defaultdict(list)

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

        loc_c, loc_s = match_errors_localization(gt_errors, det_errors, tolerance=args.tolerance)
        iou_results = match_errors_adaptive_smooth_iou(gt_errors, det_errors, report_thresholds=[0.25, 0.50, 0.75])
        print_localization_report(category, loc_c, loc_s, iou_results, args.tolerance)
        save_localization_results(category, run_name, loc_c, loc_s, out_dir)
        save_iou_localization_results(category, run_name, iou_results, out_dir)

        # === IoU-Aggregation über alle Runs ===
        # === IoU-Aggregation über alle Runs (fixed thresholds) ===
        for key in ["fixed_0.25", "fixed_0.50", "fixed_0.75"]:
            if key not in iou_results:
                continue
            tp_l, fp_l, fn_l = iou_results[key]
            th = float(key.split("_")[-1])  # "fixed_0.50" → 0.50

            agg_iou[category][th]["tp"] += len(tp_l)
            agg_iou[category][th]["fp"] += len(fp_l)
            agg_iou[category][th]["fn"] += len(fn_l)
            agg_iou[category][th]["runs"] += 1

            metrics = calculate_metrics(len(tp_l), len(fp_l), len(fn_l))
            f1_iou[category][th].append(metrics["f1"])

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
    # Finaler Gesamtbericht
    print("\n" + "═" * 160)
    print(" GESAMTVERGLEICH – HIERARCHISCH (Detection → Localization) ".center(160))
    print("═" * 160)
    print(f"{'Kategorie':<50} {'Typ':<34} {'Runs':>5} {'TP':>6} {'FP':>6} {'FN':>6} {'Prec':>8} {'Rec':>8} {'F1':>10} {'±σ':>8}")
    print("─" * 160)

    for cat in sorted(agg_det.keys()):
        runs = agg_det[cat]["runs"]

        # --- Detection ---
        md = calculate_metrics(agg_det[cat]["tp"], agg_det[cat]["fp"], agg_det[cat]["fn"])
        f1_d = mean(f1_det.get(cat, [0]))
        std_d = stdev(f1_det.get(cat, [])) if len(f1_det.get(cat, [])) > 1 else 0.0
        print(f"{cat:<50} {'Fault Detection ':<34} {runs:5} {md['tp']:6} {md['fp']:6} {md['fn']:6} "
              f"{md['precision']:8.3f} {md['recall']:8.3f} {f1_d:10.3f} ±{std_d:6.3f}")

        # --- Localization Classic & Strict ---
        mc = calculate_metrics(agg_loc_c[cat]["tp"], agg_loc_c[cat]["fp"], agg_loc_c[cat]["fn"])
        ms = calculate_metrics(agg_loc_s[cat]["tp"], agg_loc_s[cat]["fp"], agg_loc_s[cat]["fn"])
        f1_c = mean(f1_loc_c.get(cat, [0]))
        f1_s = mean(f1_loc_s.get(cat, [0]))
        std_c = stdev(f1_loc_c.get(cat, [])) if len(f1_loc_c.get(cat, [])) > 1 else 0.0
        std_s = stdev(f1_loc_s.get(cat, [])) if len(f1_loc_s.get(cat, [])) > 1 else 0.0

        print(f"{'':<50} {'Localization (Loose Overlap)':<34} {runs:5} {mc['tp']:6} {mc['fp']:6} {mc['fn']:6} "
              f"{mc['precision']:8.3f} {mc['recall']:8.3f} {f1_c:10.3f} ±{std_c:6.3f}")
        print(f"{'':<50} {'Localization (Strict IoU)':<34} {runs:5} {ms['tp']:6} {ms['fp']:6} {ms['fn']:6} "
              f"{ms['precision']:8.3f} {ms['recall']:8.3f} {f1_s:10.3f} ±{std_s:6.3f}")

        # --- IoU Thresholds 0.25 / 0.50 / 0.75 ---
        for th in [0.25, 0.50, 0.75]:
            data = agg_iou[cat][th]
            if data["runs"] == 0:
                continue
            m = calculate_metrics(data["tp"], data["fp"], data["fn"])
            f1_list = f1_iou[cat][th]
            f1_mean = mean(f1_list) if f1_list else 0.0
            f1_std  = stdev(f1_list) if len(f1_list) > 1 else 0.0
            print(f"{'':<50} {f'Localization IoU ≥ {th:.2f}':<34} {runs:5} {m['tp']:6} {m['fp']:6} {m['fn']:6} "
                  f"{m['precision']:8.3f} {m['recall']:8.3f} {f1_mean:10.3f} ±{f1_std:6.3f}")

        print("─" * 160)

    print(f"\nFertig! Alle Ergebnisse in: {out_dir}")
    print("   → fault_detection/ Ordner mit TP/FP/FN pro Run")
    print("   → Korrekte hierarchische Auswertung (Detection vor Localization)")


if __name__ == "__main__":
    main()