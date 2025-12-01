#!/usr/bin/env python3
import json
import re
from pathlib import Path
import pandas as pd

BASE_DIR = Path("docs/experiment")
RESULTS_DIR = BASE_DIR / "results"
OUTPUT_BASE = BASE_DIR / "analysis" / "Detected"

def parse_llm_json(content: str):
    content = content.strip()
    if not content:
        return []

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r'(\[.*\]|{.*})', content, re.DOTALL)
        if not match:
            return []
        data = json.loads(match.group(1))

    if isinstance(data, dict) and "bugs" in data:
        data = data["bugs"]
    elif isinstance(data, dict):
        data = [data]
    elif not isinstance(data, list):
        return []

    errors = []
    for item in data:
        if not isinstance(item, dict):
            continue

        filename = item.get("filename") or item.get("file") or item.get("path")
        if not filename:
            continue

        try:
            start_line = int(item.get("start_line") or item.get("line") or item["startLine"])
            end_line = int(item.get("end_line") or item.get("last_line") or item.get("endLine", start_line))
        except Exception:
            continue

        desc = str(item.get("error_description") or item.get("description") or item.get("message") or "").strip()
        if not desc:
            continue

        errors.append({
            "filename": Path(filename).name,
            "start_line": start_line,
            "end_line": end_line,
            "error_description": desc,
            "semantically_correct_detected": ""  # leer für manuelle Bewertung
        })
    return errors


def get_model_group(filename: str) -> str:
    name = filename.lower()
    if name.startswith("opencode_"):
        model = name[len("opencode_"):].split("_fault_bugs_")[0]
        return f"Opencode_{model}"
    else:
        # z. B. RAW_LLM_gpt-4o_fault_bugs_001.json oder gpt-4o_fault_bugs_001.json
        prefix = name.split("_fault_bugs_")[0]
        model = prefix.replace("raw_llm_", "").replace("rawllm_", "")
        return f"Raw_LLM_{model}"


def main():
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    json_files = sorted(RESULTS_DIR.glob("*_fault_bugs_*.json"))
    if not json_files:
        print("Keine *_fault_bugs_*.json Dateien in results/ gefunden!")
        return

    print(f"Gefundene Dateien: {len(json_files)}\n")

    for json_file in json_files:
        group = get_model_group(json_file.stem)
        run_folder_name = json_file.stem  # z. B. opencode_gpt-4o_fault_bugs_001

        out_dir = OUTPUT_BASE / group / run_folder_name
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            content = json_file.read_text(encoding="utf-8")
            errors = parse_llm_json(content)

            if not errors:
                print(f"{json_file.name} → keine gültigen Fehler gefunden")
                # Leere CSV trotzdem anlegen, damit man sieht, dass die Datei verarbeitet wurde
                df = pd.DataFrame(columns=["filename", "start_line", "end_line", "error_description", "semantically_correct_detected"])
            else:
                df = pd.DataFrame(errors)
                df = df[["filename", "start_line", "end_line", "error_description", "semantically_correct_detected"]]
                print(f"{json_file.name} → {len(errors)} Fehler → {out_dir}/detected_errors.csv")

            df.to_csv(out_dir / "detected_errors.csv", index=False)

        except Exception as e:
            print(f"FEHLER bei {json_file.name}: {e}")

    print(f"\nFertig! Alle CSVs liegen jetzt hier:")
    print(f"   {OUTPUT_BASE}")
    print(f"   Struktur: .../Opencode_gpt-4o/<run-name>/detected_errors.csv")
    print(f"             .../RAW_LLM_claude-3-5-sonnet/<run-name>/detected_errors.csv")


if __name__ == "__main__":
    main()