#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from datetime import datetime

RESULTS_DIR = Path("docs/experiment/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
OPENCODE_STORAGE = Path.home() / ".local/share/opencode/storage/message"


def extract_session_id(content: str, filename: str = "") -> str | None:
    match = re.search(r"\*\*Session ID:\*\*\s*(ses_[a-zA-Z0-9]+)", content, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"(ses_[a-zA-Z0-9]+)", filename, re.IGNORECASE)
    return match.group(1) if match else None


def get_model_from_session_dir(session_dir: Path) -> str:
    if not session_dir.exists():
        return "unknown_model"

    for msg_file in session_dir.glob("msg_*.json"):
        try:
            data = json.loads(msg_file.read_text(encoding="utf-8"))
            model = data.get("modelID") or data.get("model")
            if model and isinstance(model, str):
                model = model.strip()
                if "/" in model:
                    model = model.split("/", 1)[1]
                return re.sub(r"[^a-zA-Z0-9\.\-]", "", model).lower().replace(".", "-")
        except:
            continue
    return "unknown_model"


def extract_bug_json(content: str):
    start = content.find("[")
    if start == -1:
        return None

    # Alles ab dem ersten [ nehmen
    text = content[start:]

    # Nur komplette Objekte behalten
    bracket_level = 0
    objects = []
    current_pos = 0

    for i, char in enumerate(text):
        if char == '{':
            if bracket_level == 0:
                current_pos = i
            bracket_level += 1
        elif char == '}':
            bracket_level -= 1
            if bracket_level == 0:
                obj_text = text[current_pos:i+1]
                try:
                    obj = json.loads(obj_text)
                    objects.append(obj)
                except:
                    pass

    if not objects:
        return None

    print(f"   → {len(objects)} reparierte Bug-Einträge aus trunkierter Ausgabe wiederhergestellt!")
    return objects


def main():
    paths = list(Path(".").rglob("session-*.md")) if len(sys.argv) == 1 else [p for arg in sys.argv[1:] for p in Path(".").rglob(arg)]
    session_files = [p for p in paths if p.is_file() and p.suffix.lower() == ".md" and p.name.startswith("session-")]

    if not session_files:
        print("Keine 'session-*.md' Dateien gefunden!")
        return

    print(f"Verarbeite {len(session_files)} Session-Datei(en)...\n")

    for md_path in session_files:
        content = md_path.read_text(encoding="utf-8")
        session_id = extract_session_id(content, md_path.name)

        if not session_id:
            print(f"Session-ID nicht gefunden → überspringe: {md_path.name}")
            continue

        session_dir = OPENCODE_STORAGE / session_id
        model = get_model_from_session_dir(session_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        bugs = extract_bug_json(content)

        # Dateinamen
        raw_name = f"opencode_{model}_fault_raw_{timestamp}_{session_id}.md"
        bugs_name = f"opencode_{model}_fault_bugs_{timestamp}_{session_id}.json"

        raw_path = RESULTS_DIR / raw_name
        bugs_path = RESULTS_DIR / bugs_name

        # Raw speichern
        raw_path.write_text(content, encoding="utf-8")

        if bugs:
            result = {
                "_metadata": {
                    "source_file": md_path.name,
                    "model": model.replace("-", "."),
                    "session_id": session_id,
                    "processed_at": datetime.now().isoformat(),
                    "bug_count": len(bugs)
                },
                "bugs": bugs
            }
            bugs_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"{md_path.name}")
            print(f"   → {raw_name}")
            print(f"   → {bugs_name} ({len(bugs)} Bugs)\n")
        else:
            print(f"{md_path.name} → kein Bug-JSON gefunden (nur raw gespeichert)\n")

    print(f"Alle Dateien verarbeitet → {RESULTS_DIR}/")


if __name__ == "__main__":
    main()