#!/usr/bin/env python3
"""
Hashes - Detects Code changes
"""

import csv
import hashlib
import sys
from pathlib import Path

# ---------- ABSOLUT ROBUSTER ROOT-FINDER ----------
current = Path(__file__).resolve().parent
for _ in range(10):
    candidate = current / "baseline_project" / "src" / "main" / "java"
    if candidate.is_dir():
        SRC_ROOT = candidate
        PROJECT_ROOT = current
        break
    current = current.parent
else:
    print("FEHLER: baseline_project/src/main/java nicht gefunden!")
    print("Aktueller Ordner:", Path.cwd())
    print("Script-Pfad:", Path(__file__))
    sys.exit(1)

print(f"Projekt gefunden: {PROJECT_ROOT.name}")
print(f"Java-Quellen: {SRC_ROOT}")
print()

# ---------- CSV finden ----------
csv_files = list(Path.cwd().glob("*error*.csv")) + list(Path.cwd().glob("*.csv"))
csv_file = next((f for f in csv_files if "error" in f.name.lower()), None)

if not csv_file or not csv_file.is_file():
    print("FEHLER: Keine CSV mit 'error' im Namen gefunden")
    sys.exit(1)

print(f"CSV verarbeiten: {csv_file.name}")
print("-" * 60)

# ---------- Hash-Funktion ----------
def make_hash(java_file: Path, start: int, end: int) -> str:
    if not java_file.is_file():
        return "NOT_FOUND"
    try:
        lines = java_file.read_text(encoding="utf-8").splitlines()
    except:
        return "READ_ERROR"

    a = max(0, start - 1 - 5)
    b = min(len(lines), end - 1 + 5 + 1)
    context = "\n".join(line.rstrip() for line in lines[a:b])
    data = f"{java_file.as_posix()}|{start}-{end}|{context}".encode()
    return hashlib.sha256(data).hexdigest()[:16]

# ---------- Verarbeiten ----------
with csv_file.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    headers = reader.fieldnames

updated = 0
for row in rows:
    fn = row.get("filename", "").strip()
    if not fn:
        continue

    try:
        start = int(row["start_line"])
        end = int(row["end_line"]) if row.get("end_line", "").strip() else start
    except:
        continue

    java_path = SRC_ROOT / fn
    if not java_path.is_file():
        # Fallback: nur Dateiname
        matches = list(SRC_ROOT.rglob(fn))
        if matches:
            java_path = matches[0]

    new_hash = make_hash(java_path, start, end)

    old_hash = row.get("context_hash", "").strip()
    if old_hash != new_hash:
        print(f"{row['id']:4}  {fn:30}  {old_hash or 'TODO':16} → {new_hash}  {'FIXED?' if old_hash != 'TODO' else 'new'}")
        row["context_hash"] = new_hash
        updated += 1

# ---------- Zurückschreiben ----------
with csv_file.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)

# ---------- Ergebnis ----------
print("-" * 60)
if updated == 0:
    print("Kein Bug gefixt – alles noch genau so kaputt wie vorher 😭")
elif updated == 24:
    print("ALLE HASHES EINGETRAGEN!")
else:
    print(f"{updated} von 24 Bugs gefixt oder verschoben → Fix-Rate {updated/24*100:.1f}%")

print(f"\nFertig in <0.3 Sekunden. Datei aktualisiert: {csv_file.name}")