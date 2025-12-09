#!/usr/bin/env python3
import pandas as pd
import json
from sentence_transformers import SentenceTransformer, util
from pathlib import Path
from tqdm import tqdm
import sys
from collections import defaultdict

# PFADE
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

# GROUND TRUTH
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

# MODELL
print("\nLade multilingual-e5-large-instruct...")
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
model.max_seq_length = 512
gt_embeddings = model.encode(
    gt_df['error_description'].tolist(),
    convert_to_tensor=True,
    batch_size=32,
    show_progress_bar=True
)

# ALLE RUNS FINDEN
fault_files = [p for p in RESULTS_ROOT.rglob("*_fault_bugs*.json") if p.is_file()]
print(f"\n{len(fault_files)} unabhängige Runs gefunden\n")

def extract_model_name(path: Path) -> str:
    stem = path.stem
    if "_fault_bugs" in stem:
        return stem.split("_fault_bugs")[0]
    return stem

def extract_run_folder_name(path: Path) -> str:
    return path.stem

def has_overlap(a_start, a_end, b_start, b_end, tolerance=2):
    return not (a_end + tolerance < b_start or a_start - tolerance > b_end)

# METRIKEN HELPER
def compute_metrics(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return {
        "TP": tp, "FP": fp, "FN": fn,
        "Precision": round(precision, 4),
        "Recall": round(recall, 4),
        "F1": round(f1, 4)
    }

# K-WERTE FÜR RANKING
K_VALUES = [1, 3, 5, 7, 10]

# AGGREGATION
model_stats_greedy = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "runs": 0, "run_details": []})
model_stats_ranking = defaultdict(lambda: {"k_metrics": {k: [] for k in K_VALUES}, "runs": 0})

# HAUPTSCHLEIFE PRO RUN
for json_path in tqdm(fault_files, desc="Matching pro Run"):
    model_name = extract_model_name(json_path)
    run_folder = extract_run_folder_name(json_path)

    print(f"\n--- Verarbeite Run: {json_path.name} (Modell: {model_name}) ---")

    try:
        data = json.load(open(json_path, "r", encoding="utf-8"))
    except Exception as e:
        print(f"Fehler beim Lesen: {json_path} → {e}")
        continue

    # GREEDY-MATCHING
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
                if has_overlap(pred_start, pred_end, gt_start, gt_end, tolerance=2):
                    valid_gt_idxs.append(gt_idx)
            except:
                valid_gt_idxs.append(gt_idx)
        if not valid_gt_idxs:
            continue

        # Semantischer Score berechnen
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

    # Greedy 1:1 Matching -> Filename + Overlap + best semantic score = TP
    run_candidates.sort(key=lambda x: x["similarity"], reverse=True)
    assigned_gts = set()
    used_predictions = set()
    tp_list, fp_list = [], []

    for cand in run_candidates:
        if cand["gt_id"] in assigned_gts or cand["pred_id"] in used_predictions:
            fp_list.append(cand["entry"])
            used_predictions.add(cand["pred_id"])
            continue
        assigned_gts.add(cand["gt_id"])
        used_predictions.add(cand["pred_id"])
        tp_entry = cand["entry"].copy()
        tp_entry.update({
            "semantically_correct_detected": cand["gt_id"],
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

    # AUSGABE GREEDY
    model_dir = OUTPUT_ROOT / model_name
    model_dir.mkdir(exist_ok=True)
    run_dir = model_dir / run_folder
    run_dir.mkdir(exist_ok=True)

    for name, data_list in [("TP", tp_list), ("FP", fp_list), ("FN", fn_list)]:
        with open(run_dir / f"{name}.json", "w", encoding="utf-8") as f:
            json.dump(data_list, f, indent=2, ensure_ascii=False)

    tp_count = len(tp_list)
    fp_count = len(fp_list)
    fn_count = len(fn_list)
    run_summary_greedy = compute_metrics(tp_count, fp_count, fn_count)
    run_summary_greedy.update({
        "run_name": run_folder,
        "total_predictions": len(data),
        "total_ground_truth": TOTAL_GT
    })
    with open(run_dir / "summary_greedy.json", "w", encoding="utf-8") as f:
        json.dump(run_summary_greedy, f, indent=2, ensure_ascii=False)

    model_stats_greedy[model_name]["tp"] += tp_count
    model_stats_greedy[model_name]["fp"] += fp_count
    model_stats_greedy[model_name]["fn"] += fn_count
    model_stats_greedy[model_name]["runs"] += 1
    model_stats_greedy[model_name]["run_details"].append(run_summary_greedy)

    # Erstelle Mapping: Welche Vorhersage ist ein TP?
    pred_to_is_tp = {}
    for entry in data:
        pred_id = f"{entry.get('filename','')}_{entry.get('start_line','')}_{entry.get('end_line','')}"
        pred_to_is_tp[pred_id] = False
    for tp_entry in tp_list:
        pred_id = f"{tp_entry.get('filename','')}_{tp_entry.get('start_line','')}_{tp_entry.get('end_line','')}"
        pred_to_is_tp[pred_id] = True

    # Sortiere alle Vorhersagen nach Confidence für Ranking-Metriken
    ranked_predictions = sorted(data, key=lambda x: x.get("confidence", 0), reverse=True)

    # Precision@K / Recall@K basierend auf exakt denselben TPs wie Greedy
    ranking_metrics = {}
    for k in K_VALUES:
        top_k = ranked_predictions[:k]
        correct_in_top_k = 0
        for pred in top_k:
            pred_id = f"{pred.get('filename','')}_{pred.get('start_line','')}_{pred.get('end_line','')}"
            if pred_to_is_tp.get(pred_id, False):
                correct_in_top_k += 1

        precision_k = correct_in_top_k / k if k > 0 else 0.0
        recall_k = correct_in_top_k / TOTAL_GT if TOTAL_GT > 0 else 0.0

        ranking_metrics[f"Precision@{k}"] = round(precision_k, 4)
        ranking_metrics[f"Recall@{k}"] = round(recall_k, 4)

    # Speichere Ranking
    ranking_summary = {
        "run_name": run_folder,
        "total_predictions": len(data),
        "total_ground_truth": TOTAL_GT,
        **ranking_metrics
    }
    with open(run_dir / "summary_ranking_confidence.json", "w", encoding="utf-8") as f:
        json.dump(ranking_summary, f, indent=2, ensure_ascii=False)

    for k in K_VALUES:
        model_stats_ranking[model_name]["k_metrics"][k].extend([
            ranking_summary[f"Precision@{k}"],
            ranking_summary[f"Recall@{k}"]
        ])
    model_stats_ranking[model_name]["runs"] += 1

    print(f"→ {run_folder} | Greedy F1: {run_summary_greedy['F1']:.4f} | "
          f"P@5: {ranking_metrics['Precision@5']:.4f} | R@5: {ranking_metrics['Recall@5']:.4f}")

# MODEL SUMMARIES
print("\n" + "="*80)
print("SCHREIBE MODEL_SUMMARY.JSON")
print("="*80)

for model_name in set(model_stats_greedy.keys()) | set(model_stats_ranking.keys()):
    model_dir = OUTPUT_ROOT / model_name

    if model_name in model_stats_greedy:
        stats = model_stats_greedy[model_name]
        n = stats["runs"]
        model_summary = compute_metrics(stats["tp"], stats["fp"], stats["fn"])
        model_summary.update({
            "model": model_name,
            "evaluation_type": "greedy_1to1_best_semantic",
            "total_runs": n,
            "total_TP": stats["tp"],
            "total_FP": stats["fp"],
            "total_FN": stats["fn"],
            "total_ground_truth": TOTAL_GT,
            "per_run_details": stats["run_details"]
        })
        with open(model_dir / "model_summary_greedy.json", "w", encoding="utf-8") as f:
            json.dump(model_summary, f, indent=2, ensure_ascii=False)

    if model_name in model_stats_ranking:
        stats = model_stats_ranking[model_name]
        ranking_avg = {}
        for k in K_VALUES:
            precs = stats["k_metrics"][k][::2]
            recs = stats["k_metrics"][k][1::2]
            ranking_avg[f"avg_Precision@{k}"] = round(sum(precs)/len(precs), 4) if precs else 0
            ranking_avg[f"avg_Recall@{k}"] = round(sum(recs)/len(recs), 4) if recs else 0

        ranking_model_summary = {
            "model": model_name,
            "evaluation_type": "ranking_by_confidence_consistent_with_greedy",
            "total_runs": stats["runs"],
            "total_ground_truth": TOTAL_GT,
            **ranking_avg
        }
        with open(model_dir / "model_summary_ranking_confidence.json", "w", encoding="utf-8") as f:
            json.dump(ranking_model_summary, f, indent=2, ensure_ascii=False)

        print(f"{model_name:30} → Greedy F1: {model_summary['F1'] if 'model_summary' in locals() else '-':.4f} | "
              f"P@5: {ranking_avg['avg_Precision@5']:.4f} | R@5: {ranking_avg['avg_Recall@5']:.4f}")

print("\n" + "="*100)
print("FERTIG!")
print("Dateien: summary_greedy.json + summary_ranking_confidence.json")
print("="*100)