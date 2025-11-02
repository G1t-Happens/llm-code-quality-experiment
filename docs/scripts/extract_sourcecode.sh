#!/usr/bin/env bash
# ==============================================================================
# extract_sourcecode.sh - Rekursiv Dateien mit bestimmten Endungen extrahieren
# ==============================================================================
set -Eeuo pipefail
IFS=$'\n\t'

PROJECT_PATH="."
OUTPUT_FILE="extracted_sources.txt"
EXTENSIONS=()
EXCLUDE_DIRS=(".git" "node_modules" "target" "build" "gradle" ".idea" ".vscode" ".venv" "*/generated/*")

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  -p, --path <path>        Projektverzeichnis (default: aktuelles Verzeichnis)
  -o, --output <file>      Ausgabedatei (default: extracted_sources.txt)
  -e, --ext <.ext ...>     Liste der Dateiendungen, z.B. -e .java .groovy .xml
  -x, --exclude <dir ...>  Weitere Verzeichnisse oder Pfade, die ausgeschlossen werden sollen
  -h, --help               Diese Hilfe anzeigen

Beispiel:
  ./extract_sourcecode.sh -p ~/workspace/myapp -o all_code.txt -e .java .groovy -x ~/workspace/myapp/test
EOF
}

# -----------------------------
# Optionen parsen
# -----------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        -p|--path)
            [[ $# -ge 2 ]] || { echo "❌ Fehlender Pfad für -p" >&2; exit 1; }
            PROJECT_PATH="$2"; shift 2 ;;
        -o|--output)
            [[ $# -ge 2 ]] || { echo "❌ Fehlende Datei für -o" >&2; exit 1; }
            OUTPUT_FILE="$2"; shift 2 ;;
        -e|--ext)
            shift
            while [[ $# -gt 0 && ! "$1" =~ ^- ]]; do
                [[ "$1" == .* ]] || EXTENSIONS+=(".${1}")
                [[ "$1" == .* ]] && EXTENSIONS+=("$1")
                shift
            done ;;
        -x|--exclude)
            shift
            while [[ $# -gt 0 && ! "$1" =~ ^- ]]; do
                EXCLUDE_DIRS+=("$1")
                shift
            done ;;
        -h|--help)
            usage; exit 0 ;;
        *)
            echo "❌ Unbekannte Option: $1" >&2; usage; exit 1 ;;
    esac
done

# -----------------------------
# Validierung
# -----------------------------
if [[ ${#EXTENSIONS[@]} -eq 0 ]]; then
    echo "❌ Bitte mindestens eine Dateiendung mit -e angeben." >&2
    exit 1
fi

if [[ ! -d "$PROJECT_PATH" ]]; then
    echo "❌ Ungültiger Projektpfad: $PROJECT_PATH" >&2
    exit 1
fi

# -----------------------------
# Absolute Pfade
# -----------------------------
PROJECT_PATH="$(realpath "$PROJECT_PATH")"
OUTPUT_FILE="$(realpath "$(dirname "$OUTPUT_FILE")")/$(basename "$OUTPUT_FILE")"

# Exclude-Pfade normalisieren
for i in "${!EXCLUDE_DIRS[@]}"; do
    # Nur absolute Pfade normalisieren, glob Patterns wie */generated/* bleiben unverändert
    [[ "${EXCLUDE_DIRS[$i]}" == *"*"* ]] && continue
    EXCLUDE_DIRS[$i]="$(realpath -m "${EXCLUDE_DIRS[$i]}")"
done

printf "📂 Projekt: %s\n📝 Ausgabe: %s\n🔍 Endungen: %s\n🚫 Ausschlüsse: %s\n--------------------------------------\n" \
       "$PROJECT_PATH" "$OUTPUT_FILE" "${EXTENSIONS[*]}" "${EXCLUDE_DIRS[*]}"

: > "$OUTPUT_FILE"

# -----------------------------
# find Argumente bauen
# -----------------------------
find_args=( "$PROJECT_PATH" -type f )

# Endungen
ext_expr=()
for ext in "${EXTENSIONS[@]}"; do
    ext_expr+=( -iname "*${ext}" -o )
done
if ((${#ext_expr[@]})); then unset 'ext_expr[-1]'; fi
find_args+=( \( "${ext_expr[@]}" \) )

# Excludes
for ex in "${EXCLUDE_DIRS[@]}"; do
    if [[ "$ex" == *"*"* ]]; then
        find_args+=( -not -path "$ex" )
    else
        find_args+=( -not -path "${ex}/*" )
    fi
done

# -----------------------------
# Dateien finden
# -----------------------------
mapfile -d '' FILES < <(LC_ALL=C find "${find_args[@]}" -print0 2>/dev/null | sort -z)

printf "📄 Gefundene Dateien: %d\n--------------------------------------\n" "${#FILES[@]}"

# -----------------------------
# Dateien extrahieren
# -----------------------------
{
    for file in "${FILES[@]}"; do
        printf "\n===== FILE: %s =====\n\n" "$file"
        # Binärdateien überspringen
        if file --mime "$file" | grep -qE 'binary|image|application'; then
            printf "[⚠️ Übersprungen (binär): %s]\n" "$file"
            continue
        fi
        # UTF-8 konvertieren
        if ! iconv -f utf-8 -t utf-8 -c "$file" 2>/dev/null; then
            cat "$file" 2>/dev/null || printf "[⚠️ Fehler beim Lesen von %s]\n" "$file"
        fi
    done
} >> "$OUTPUT_FILE"

printf "✅ Fertig. Ausgabe geschrieben nach: %s\n" "$OUTPUT_FILE"
