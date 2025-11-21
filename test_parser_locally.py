#!/usr/bin/env python3
import argparse
from pathlib import Path

# ----------------------------- Pfade anpassn -----------------------------
BASE_DIR = Path(__file__).parent.resolve()
GENERATED_TESTS_DIR = BASE_DIR / "baseline_project" / "src" / "test" / "java"
RESULTS_DIR = BASE_DIR / "docs" / "experiment" / "results"

GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------- exakt wie im finalen Scriptt -----------------------------
def resolve_test_path(marker_path: str) -> Path:
    path = Path(marker_path.strip())

    if "src/test/java" in path.parts:
        idx = list(path.parts).index("src/test/java")
    elif "src/main/java" in path.parts:
        idx = list(path.parts).index("src/main/java")
    else:
        # Fallback
        try:
            com_idx = list(path.parts).index("com")
            relative_parts = path.parts[com_idx:]
            test_path = GENERATED_TESTS_DIR.joinpath(*relative_parts)
        except ValueError:
            raise ValueError(f"Unbekannter Pfad-Typ: {marker_path}")
        else:
            # Sicherstellen, dass es ein Test ist
            if not test_path.name.endswith("Test.java"):
                stem = test_path.stem + "Test" if not test_path.stem.endswith("Test") else test_path.stem
                test_path = test_path.with_name(stem + ".java")
            test_path.parent.mkdir(parents=True, exist_ok=True)
            return test_path

    relative = path.parts[idx + 1 :]
    test_path = GENERATED_TESTS_DIR.joinpath(*relative)

    # Test-Suffix sicherstellen
    if not test_path.name.endswith("Test.java"):
        stem = test_path.stem
        if not stem.endswith("Test"):
            stem += "Test"
        test_path = test_path.with_name(stem + ".java")

    test_path.parent.mkdir(parents=True, exist_ok=True)
    return test_path


def save_generated_test(file_marker: str, content: str):
    if not file_marker.strip().startswith("===== FILE:"):
        print("Ungültiger Marker, überspringe...")
        return

    path_str = file_marker[len("===== FILE:"):].strip().split("=====", 1)[0].strip()
    if not path_str:
        return

    try:
        test_path = resolve_test_path(path_str)
    except Exception as e:
        print(f"Pfad-Fehler: {e} → überspringe {path_str}")
        return

    # Package ableiten
    try:
        p = Path(path_str)
        com_idx = list(p.parts).index("com")
        package = ".".join(p.parts[com_idx:-1])
    except:
        package = "com.llmquality.baseline"

    java_content = content.strip()
    if not java_content.startswith("package "):
        java_content = f"package {package};\n\n{java_content}"

    test_path.write_text(java_content, encoding="utf-8")
    print(f"Test gespeichert → {test_path}")


def parse_raw_file(raw_file_path: Path):
    print(f"Lese Raw-Datei: {raw_file_path}")
    content = raw_file_path.read_text(encoding="utf-8")

    print("Extrahiere Tests...")
    current_content = ""
    current_marker = None

    for raw_line in content.splitlines(keepends=True):
        if "===== FILE:" in raw_line:
            if current_marker and current_content.strip():
                save_generated_test(current_marker, current_content)

            start_idx = raw_line.find("===== FILE:") + len("===== FILE:")
            path_part = raw_line[start_idx:].strip()
            clean_path = path_part.split("=====", 1)[0].strip()

            current_marker = "===== FILE: " + clean_path
            current_content = ""
            print(f"Neuer Block → {clean_path}")
        else:
            current_content += raw_line

    if current_marker and current_content.strip():
        save_generated_test(current_marker, current_content)

    print(f"\nFertig! Tests liegen in:\n   {GENERATED_TESTS_DIR}\n")


# ----------------------------- CLI -----------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_file", help="Pfad zur grok_tests_raw_*.txt Datei")
    args = parser.parse_args()

    raw_path = Path(args.raw_file)
    if not raw_path.exists():
        print(f"Datei nicht gefunden: {raw_path}")
    else:
        parse_raw_file(raw_path)