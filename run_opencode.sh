#!/usr/bin/env bash
# run_opencode.sh

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/baseline_project"
RESULTS_ROOT="$SCRIPT_DIR/docs/experiment/results/opencode"

mkdir -p "$RESULTS_ROOT/raw_sessions" "$RESULTS_ROOT/parsed_sessions"

echo "Starte OpenCode in: $PROJECT_DIR"
echo "Ergebnisse → $RESULTS_ROOT"
echo

# Session vor Start merken
LATEST_BEFORE=$(ls -dt ~/.local/share/opencode/storage/message/ses_* 2>/dev/null | head -n1 || echo "none")

cd "$PROJECT_DIR"
opencode "$@"

# Warte auf neue Session
echo
echo "Session beendet – warte auf neue Session..."
sleep 10

LATEST_AFTER=$(ls -dt ~/.local/share/opencode/storage/message/ses_* 2>/dev/null | head -n1)

if [ -z "$LATEST_AFTER" ] || [ "$LATEST_AFTER" = "$LATEST_BEFORE" ]; then
    echo "Keine neue Session gefunden – Abbruch."
    exit 1
fi

SES_DIR="$LATEST_AFTER"
SES_ID="$(basename "$SES_DIR")"
TARGET_RAW="$RESULTS_ROOT/raw_sessions/$SES_ID"
TARGET_JSON="$RESULTS_ROOT/parsed_sessions/$SES_ID.json"

TIMESTAMP=$(date +"%Y-%m-%dT%H-%M-%S")
MODEL=${OPENCODE_MODEL:-unknown}
MODEL=${MODEL##*/}

echo "Neue Session erkannt: $SES_ID"

# Roh-Session kopieren
echo "Kopiere Rohdaten..."
rsync -a --quiet "$SES_DIR/" "$TARGET_RAW/" 2>/dev/null || \
    cp -r "$SES_DIR"/* "$TARGET_RAW/" 2>/dev/null || true
echo "Roh-Session gesichert → raw_sessions/$SES_ID"

# PARSER - Opencode erlaubt kein Response Schema
echo "Extrahiere & repariere JSON aus summary.body / content..."

TMP_ALL=$(mktemp)
TMP_OUT=$(mktemp)
TMP_ERR=$(mktemp)

cat "$TARGET_RAW"/*.json > "$TMP_ALL" 2>/dev/null

python3 - "$TMP_ALL" "$TMP_OUT" "$TMP_ERR" "$SES_ID" << 'EOF'
import sys, json, re

input_file, output_file, error_file, ses_id = sys.argv[1:]

with open(input_file, 'r', encoding='utf-8') as f:
    data = f.read()

blocks = []

# 1. summary.body (robust gegen alles)
for m in re.finditer(r'"summary"\s*:\s*\{[^}]*"body"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', data, re.DOTALL):
    escaped = m.group(1)
    try:
        body = escaped.encode('utf-8').decode('unicode_escape')
        if any(k in body for k in ['severity', 'filename', 'error_description', '[', '{']):
            blocks.append(body.strip())
    except:
        pass

# 2. Fallback: content
for m in re.finditer(r'"content"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', data, re.DOTALL):
    escaped = m.group(1)
    try:
        content = escaped.encode('utf-8').decode('unicode_escape')
        if any(k in content for k in ['severity', 'filename', '[', '{']):
            blocks.append(content.strip())
    except:
        pass

# Entduplizieren
seen = set()
unique_blocks = [b for b in blocks if b not in seen and (seen.add(b) or True)]

final = []

for idx, raw in enumerate(unique_blocks):
    s = raw.strip()

    # Remove code fences
    s = re.sub(r'^```json\s*\n|```$', '', s, flags=re.MULTILINE|re.IGNORECASE)
    s = re.sub(r'^```\w*\n', '', s, flags=re.MULTILINE)

    # Try direct parse
    try:
        obj = json.loads(s)
        if isinstance(obj, list):
            final.extend(obj)
        elif isinstance(obj, dict):
            final.append(obj)
        continue
    except:
        pass

    # Repair
    s2 = re.sub(r'(\{|\,)\s*([a-zA-Z_]\w*)\s*:', r'\1 "\2":', s)
    s2 = re.sub(r',\s*(\}|])', r'\1', s2)
    s2 = re.sub(r'\}\s*\{', '},{', s2)
    s2 = re.sub(r'\]\s*\[', '],[', s2)

    try:
        obj = json.loads(s2)
        if isinstance(obj, list):
            final.extend(obj)
        elif isinstance(obj, dict):
            final.append(obj)
        continue
    except:
        pass

    # Last resort: einzelne Objekte mit "severity"
    for obj_str in re.findall(r'\{[^}{]*"severity"[^}{]*\}', s2, re.DOTALL):
        try:
            parsed = json.loads(obj_str)
            if isinstance(parsed, dict) and "severity" in parsed:
                final.append(parsed)
        except:
            continue

# Schreibe finales Array
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(final, f, indent=2, ensure_ascii=False, sort_keys=True)

print(f"SUCCESS: {len(final)} Fehler extrahiert → {ses_id}.json")
EOF

# Speichern & Symlink
cp "$TMP_OUT" "$TARGET_JSON"
ln -sf "$SES_ID.json" "$RESULTS_ROOT/parsed_sessions/parsed_latest.json" 2>/dev/null || true

COUNT=$(python3 -c "import json,sys; print(len(json.load(open('$TARGET_JSON','r'))))" 2>/dev/null || echo 0)

# Fertig
echo
echo "ALLES FERTIG – 100% ERFOLG!"
echo "   Session:        $SES_ID"
echo "   Rohdaten:       raw_sessions/$SES_ID/"
echo "   Ergebnis:       parsed_sessions/$SES_ID.json"
echo "   Anzahl Fehler:  $COUNT"
echo "   Latest-Symlink: parsed_latest.json → $SES_ID.json"
echo
echo "DONE."

rm -f "$TMP_ALL" "$TMP_OUT" "$TMP_ERR"

exit 0