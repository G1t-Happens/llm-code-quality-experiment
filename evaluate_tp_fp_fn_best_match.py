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

if not GT_PATH.exists():
    sys.exit("Ground Truth nicht gefunden!")

# Ground Truth
gt_df = pd.read_csv(GT_PATH)
gt_df['filename'] = gt_df['filename'].astype(str).str.strip()
gt_df['error_description'] = gt_df['error_description'].astype(str).str.strip()
gt_df['basename'] = gt_df['filename'].apply(lambda x: Path(x).name)
gt_df = gt_df.reset_index(drop=True)
print(f"Ground Truth geladen: {len(gt_df)} injizierte Bugs")

gt_by_basename = defaultdict(list)
for idx, row in gt_df.iterrows():
    gt_by_basename[row['basename']].append(idx)

# Embedding-Modell
print("\nLade multilingual-e5-large-instruct...")
model = SentenceTransformer("intfloat/multilingual-e5-large-instruct")
model.max_seq_length = 512
gt_embeddings = model.encode(
    gt_df['error_description'].tolist(),
    convert_to_tensor=True,
    batch_size=32,
    show_progress_bar=True
)

# Alle Rohdaten-Runs finden
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

# Neue Output-Struktur
OUTPUT_ROOT = EXPERIMENT_ROOT / "analysis"
OUTPUT_ROOT.mkdir(exist_ok=True)

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

    # Kandidaten sammeln – jetzt OHNE Threshold
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

        # Nur Dateien mit Ground Truth in Betracht ziehen
        if pred_basename not in gt_by_basename:
            continue

        # Finde alle GT-Einträge mit Zeilenüberlappung (oder alle, falls keine Zeilenangabe)
        valid_gt_idxs = []
        for gt_idx in gt_by_basename[pred_basename]:
            row = gt_df.iloc[gt_idx]
            try:
                gt_start = int(row["start_line"])
                gt_end = int(row["end_line"])
                if has_overlap(pred_start, pred_end, gt_start, gt_end):
                    valid_gt_idxs.append(gt_idx)
            except:
                valid_gt_idxs.append(gt_idx)  # Falls Zeilen fehlen → alle als möglich

        if not valid_gt_idxs:
            continue

        # Embedding der Vorhersage berechnen
        pred_emb = model.encode(pred_desc, convert_to_tensor=True)
        scores = util.cos_sim(pred_emb, gt_embeddings)[0]

        # Für jeden validen GT-Eintrag einen Kandidaten anlegen
        for gt_idx in valid_gt_idxs:
            score = scores[gt_idx].item()
            run_candidates.append({
                "entry": entry,
                "pred_id": entry["_pred_id"],
                "gt_id": gt_df.iloc[gt_idx]["id"],
                "similarity": score,
                "pred_file": pred_file_full
            })

    # --- Greedy 1:1 Matching nach höchstem Similarity-Score ---
    run_candidates.sort(key=lambda x: x["similarity"], reverse=True)

    assigned_gts = set()
    used_predictions = set()
    tp_list, fp_list = [], []

    for cand in run_candidates:
        gt_id = cand["gt_id"]
        pred_id = cand["pred_id"]

        # Bereits vergebener GT oder bereits genutzte Prediction → FP
        if gt_id in assigned_gts or pred_id in used_predictions:
            fp_list.append(cand["entry"])
            used_predictions.add(pred_id)   # Auch FP markieren wir als "verbraucht"
            continue

        # Sonst: TP!
        assigned_gts.add(gt_id)
        used_predictions.add(pred_id)

        tp_entry = cand["entry"].copy()
        tp_entry.update({
            "semantically_correct_detected": gt_id,
            "similarity_score": round(cand["similarity"], 4),
            "matching_method": "per_run_basename_overlap_best_semantic"  # Name angepasst
        })
        tp_list.append(tp_entry)

    # Alle nicht gematchten Predictions sind FP
    for entry in data:
        if entry["_pred_id"] not in used_predictions:
            fp_list.append(entry)

    # Alle nicht gefundenen GTs sind FN
    fn_list = [
        row.to_dict()
        for _, row in gt_df.iterrows()
        if row["id"] not in assigned_gts
    ]

    # Aufräumen
    for lst in (tp_list, fp_list):
        for e in lst:
            e.pop("_pred_id", None)

    # Ausgabe
    model_dir = OUTPUT_ROOT / model_name
    model_dir.mkdir(exist_ok=True)

    run_dir = model_dir / run_folder
    run_dir.mkdir(exist_ok=True)

    for name, data_list in [("TP", tp_list), ("FP", fp_list), ("FN", fn_list)]:
        with open(run_dir / f"{name}.json", "w", encoding="utf-8") as f:
            json.dump(data_list, f, indent=2, ensure_ascii=False)

    print(f"→ {run_folder}: {len(tp_list)} TP, {len(fp_list)} FP, {len(fn_list)} FN "
          f"(Preds: {len(data)}), basierend auf bestem Semantic-Match (kein Threshold)")

# Fertig
print("\n" + "="*100)
print(f"Ausgabe in: {OUTPUT_ROOT}")
print("="*100)