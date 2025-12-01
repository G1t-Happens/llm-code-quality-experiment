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
    if not session_dir.exists() or not session_dir.is_dir():
        return "unknown_model"

    for msg_file in session_dir.glob("msg_*.json"):
        try:
            data = json.loads(msg_file.read_text(encoding="utf-8"))
            model = data.get("modelID") or data.get("model")
            if model and isinstance(model, str):
                model = model.strip()
                if "/" in model:
                    model = model.split("/", 1)[1]
                cleaned = re.sub(r"[^a-zA-Z0-9\.\-]", "", model)
                return cleaned.lower().replace(".", "-")
        except Exception:
            continue
    return "unknown_model"


def extract_bug_json(content: str):
    start = content.find("[")
    if start == -1:
        return None

    text = content[start:]
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
                except json.JSONDecodeError:
                    pass

    if not objects:
        return None

    print(f"   → {len(objects)} reparierte Bug-Einträge wiederhergestellt!")
    return objects


def make_safe_filename(part: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", part).strip("_")


def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        new_path = path.parent / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


def main():
    if len(sys.argv) <= 1:
        print("Usage: python opencode_bug_extractor.py <file1.md> [file2.md ...] oder Ordner")
        print("       Oder alle .md im aktuellen Verzeichnis: python opencode_bug_extractor.py *.md")
        sys.exit(1)

    # Alle Argumente als Pfade behandeln – auch Wildcards wie *.md werden vom Shell expanded
    input_paths = [Path(p) for p in sys.argv[1:]]

    # Falls Pfad ein Ordner → alle .md darin nehmen
    md_files = []
    for p in input_paths:
        if p.is_dir():
            md_files.extend(p.rglob("*.md"))
        elif p.is_file() and p.suffix.lower() == ".md":
            md_files.append(p)
        else:
            print(f"Überspringe (keine .md-Datei): {p}")

    if not md_files:
        print("Keine .md-Dateien gefunden!")
        return

    print(f"Verarbeite {len(md_files)} Markdown-Datei(en)...\n")

    for md_path in md_files:
        print(f"→ Bearbeite: {md_path.name}")
        content = md_path.read_text(encoding="utf-8")
        session_id = extract_session_id(content, md_path.name)

        if not session_id:
            print(f"   Session-ID nicht gefunden → nur raw speichern\n")
        else:
            session_dir = OPENCODE_STORAGE / session_id
            model = get_model_from_session_dir(session_dir)
        # Fallback-Modell falls Session nicht existiert
        model = model if session_id else "unknown_model"

        safe_stem = make_safe_filename(md_path.stem)
        unique_id = f"{safe_stem}_{session_id or 'no_session'}"

        raw_name = f"opencode_{model}_fault_raw_{unique_id}.md"
        bugs_name = f"opencode_{model}_fault_bugs_{unique_id}.json"

        raw_path = ensure_unique_path(RESULTS_DIR / raw_name)
        bugs_path = ensure_unique_path(RESULTS_DIR / bugs_name)

        raw_path.write_text(content, encoding="utf-8")

        bugs = extract_bug_json(content)

        if bugs:
            result = {
                "_metadata": {
                    "source_file": md_path.name,
                    "source_path": str(md_path.resolve()),
                    "model": model.replace("-", "."),
                    "session_id": session_id,
                    "processed_at": datetime.now().isoformat(),
                    "bug_count": len(bugs)
                },
                "bugs": bugs
            }
            bugs_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"   → {raw_path.name}")
            print(f"   → {bugs_path.name} ({len(bugs)} Bugs)\n")
        else:
            print(f"   → Nur raw gespeichert (kein Bug-JSON gefunden)\n")

    print(f"\nFertig! Ergebnisse in: {RESULTS_DIR.resolve()}")


if __name__ == "__main__":
    main()