#!/usr/bin/env python3
import pandas as pd
import json
from sentence_transformers import SentenceTransformer, util
from pathlib import Path
from tqdm import tqdm
import sys
from collections import defaultdict

# Pfade
BASE_DIR = Path.cwd()
possible_roots = [BASE_DIR / "docs" / "experiment", BASE_DIR / "experiment"]
EXPERIMENT_ROOT = next((p for p in possible_roots if p.exists()), None)
if not EXPERIMENT_ROOT:
    sys.exit("Experiment-Ordner nicht gefunden!")

GT_PATH = EXPERIMENT_ROOT / "ground_truth" / "seeded_errors_iso25010.csv"
RESULTS_ROOT = EXPERIMENT_ROOT / "results"
OUTPUT_ROOT = EXPERIMENT_ROOT / "analysis"
OUTPUT_ROOT.mkdir(exist_ok=True)

if not GT_PATH.exists():
    sys.exit("Ground Truth nicht gefunden!")

# Ground Truth laden
gt_df = pd.read_csv(GT_PATH)
gt_df['filename'] = gt_df['filename'].astype(str).str.strip()
gt_df['error_description'] = gt_df['error_description'].astype(str).str.strip()
gt_df['basename'] = gt_df['filename'].apply(lambda x: Path(x).name)
gt_df = gt_df.reset_index(drop=True)
TOTAL_GT = len(gt_df)
print(f"Ground Truth geladen: {TOTAL_GT} injizierte Bugs")

gt_by_basename = defaultdict(list)
for idx, row in gt_df.iterrows():
    gt_by_basename[row['basename']].append(idx)

# Modell laden
print("\nLade multilingual-e5-large-instruct...")
model = SentenceTransformer("intfloat/multilingual-e5-large-instruct")
model.max_seq_length = 512
gt_embeddings = model.encode(
    gt_df['error_description'].tolist(),
    convert_to_tensor=True,
    batch_size=32,
    show_progress_bar=True
)

# Alle Runs finden
fault_files = [p for p in RESULTS_ROOT.rglob("*_fault_bugs*.json") if p.is_file()]
print(f"\n{len(fault_files)} unabhängige Runs gefunden\n")

def extract_model_name(path: Path) -> str:
    stem = path.stem
    if "_fault_bugs" in stem:
        return stem.split("_fault_bugs")[0]
    return stem

def extract_run_folder_name(path: Path) -> str:
    return path.stem

def has_overlap(a_start, a_end, b_start, b_end):
    return not (a_end < b_start or a_start > b_end)

# Für Modell-Übergreifende Aggregation
model_stats = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "runs": 0, "run_details": []})

# Hilfsfunktion für Metriken
def compute_metrics(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return {
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "Precision": round(precision, 4),
        "Recall": round(recall, 4),
        "F1": round(f1, 4)
    }

# Verarbeitung pro Run
for json_path in tqdm(fault_files, desc="Matching pro Run"):
    model_name = extract_model_name(json_path)
    run_folder = extract_run_folder_name(json_path)

    print(f"\n--- Verarbeite Run: {json_path.name} (Modell: {model_name}) ---")

    try:
        data = json.load(open(json_path, "r", encoding="utf-8"))
    except Exception as e:
        print(f"Fehler beim Lesen: {json_path} → {e}")
        continue

    for entry in data:
        entry["_pred_id"] = f"{entry.get('filename','')}_{entry.get('start_line','')}_{entry.get('end_line','')}"

    run_candidates = []

    for entry in data:
        pred_file_full = str(entry.get("filename") or "").strip()
        pred_basename = Path(pred_file_full).name
        pred_desc = str(entry.get("error_description") or "").strip()

        if not pred_file_full or not pred_desc:
            continue
        try:
            pred_start = int(entry["start_line"])
            pred_end = int(entry["end_line"])
        except:
            continue
        if pred_basename not in gt_by_basename:
            continue

        valid_gt_idxs = []
        for gt_idx in gt_by_basename[pred_basename]:
            row = gt_df.iloc[gt_idx]
            try:
                gt_start = int(row["start_line"])
                gt_end = int(row["end_line"])
                if has_overlap(pred_start, pred_end, gt_start, gt_end):
                    valid_gt_idxs.append(gt_idx)
            except:
                valid_gt_idxs.append(gt_idx)
        if not valid_gt_idxs:
            continue

        pred_emb = model.encode(pred_desc, convert_to_tensor=True)
        scores = util.cos_sim(pred_emb, gt_embeddings)[0]

        for gt_idx in valid_gt_idxs:
            score = scores[gt_idx].item()
            run_candidates.append({
                "entry": entry,
                "pred_id": entry["_pred_id"],
                "gt_id": gt_df.iloc[gt_idx]["id"],
                "similarity": score,
                "pred_file": pred_file_full
            })

    # Greedy Matching: höchster Score gewinnt
    run_candidates.sort(key=lambda x: x["similarity"], reverse=True)

    assigned_gts = set()
    used_predictions = set()
    tp_list, fp_list = [], []

    for cand in run_candidates:
        gt_id = cand["gt_id"]
        pred_id = cand["pred_id"]

        if gt_id in assigned_gts or pred_id in used_predictions:
            fp_list.append(cand["entry"])
            used_predictions.add(pred_id)
            continue

        assigned_gts.add(gt_id)
        used_predictions.add(pred_id)

        tp_entry = cand["entry"].copy()
        tp_entry.update({
            "semantically_correct_detected": gt_id,
            "similarity_score": round(cand["similarity"], 4),
            "matching_method": "per_run_basename_overlap_best_semantic"
        })
        tp_list.append(tp_entry)

    for entry in data:
        if entry["_pred_id"] not in used_predictions:
            fp_list.append(entry)

    fn_list = [row.to_dict() for _, row in gt_df.iterrows() if row["id"] not in assigned_gts]

    for lst in (tp_list, fp_list):
        for e in lst:
            e.pop("_pred_id", None)

    # Ausgabe TP/FP/FN
    model_dir = OUTPUT_ROOT / model_name
    model_dir.mkdir(exist_ok=True)
    run_dir = model_dir / run_folder
    run_dir.mkdir(exist_ok=True)

    for name, data_list in [("TP", tp_list), ("FP", fp_list), ("FN", fn_list)]:
        with open(run_dir / f"{name}.json", "w", encoding="utf-8") as f:
            json.dump(data_list, f, indent=2, ensure_ascii=False)

    # Summary pro Run
    tp_count = len(tp_list)
    fp_count = len(fp_list)
    fn_count = len(fn_list)

    run_summary = compute_metrics(tp_count, fp_count, fn_count)
    run_summary["run_name"] = run_folder
    run_summary["total_predictions"] = len(data)
    run_summary["total_ground_truth"] = TOTAL_GT

    with open(run_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(run_summary, f, indent=2, ensure_ascii=False)

    # Aggregation für Modell-Summary
    model_stats[model_name]["tp"] += tp_count
    model_stats[model_name]["fp"] += fp_count
    model_stats[model_name]["fn"] += fn_count
    model_stats[model_name]["runs"] += 1
    model_stats[model_name]["run_details"].append(run_summary)

    print(f"→ {run_folder}: TP={tp_count} | FP={fp_count} | FN={fn_count} | "
          f"P={run_summary['Precision']:.4f} | R={run_summary['Recall']:.4f} | F1={run_summary['F1']:.4f}")

# SUMMARY
print("\n" + "="*80)
print("SCHREIBE MODELL-SUMMARIES (gemittelt über alle Runs)")
print("="*80)

for model_name, stats in model_stats.items():
    n = stats["runs"]
    avg_tp = stats["tp"] / n
    avg_fp = stats["fp"] / n
    avg_fn = stats["fn"] / n

    # Macro-Average über alle Runs
    model_summary = compute_metrics(stats["tp"], stats["fp"], stats["fn"])
    model_summary.update({
        "model": model_name,
        "total_runs": n,
        "avg_TP_per_run": round(avg_tp, 2),
        "avg_FP_per_run": round(avg_fp, 2),
        "avg_FN_per_run": round(avg_fn, 2),
        "total_TP": stats["tp"],
        "total_FP": stats["fp"],
        "total_FN": stats["fn"],
        "total_ground_truth": TOTAL_GT,
        "per_run_details": stats["run_details"]
    })

    model_dir = OUTPUT_ROOT / model_name
    with open(model_dir / "model_summary.json", "w", encoding="utf-8") as f:
        json.dump(model_summary, f, indent=2, ensure_ascii=False)

    print(f"{model_name:30} → F1: {model_summary['F1']:.4f}  "
          f"(P: {model_summary['Precision']:.4f}, R: {model_summary['Recall']:.4f}) "
          f"über {n} Runs")

print("\n" + "="*100)
print("FERTIG – Alle TP/FP/FN + summary.json pro Run + model_summary.json pro Modell!")
print(f"Alle Ergebnisse in: {OUTPUT_ROOT}")
print("="*100)