#!/usr/bin/env python3
import shutil
import subprocess
import re
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLEAN = ROOT / "baseline_project_clean"
BUGGY = ROOT / "baseline_project_buggy"
GROUND_TRUTH_CSV = ROOT / "docs/experiment/ground_truth/seeded_errors_iso25010.csv"

# Regex für @Test, @ParameterizedTest usw.
TEST_PATTERN = re.compile(
    r'^\s*@(?:org\.junit\.jupiter\.api\.)?(Test|ParameterizedTest|RepeatedTest|TestFactory|TestTemplate)\b',
    re.MULTILINE
)

def copy_tests():
    src = CLEAN / "src/test/java"
    dst = BUGGY / "src/test/java"
    if not src.exists():
        print("Keine Tests im clean Projekt!")
        return False
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return True

def count_generated_tests() -> int:
    total = 0
    test_dir = CLEAN / "src/test/java"
    if not test_dir.exists():
        return 0
    for java_file in test_dir.rglob("*.java"):
        try:
            content = java_file.read_text(encoding="utf-8", errors="ignore")
            total += len(TEST_PATTERN.findall(content))
        except:
            continue
    return total

def get_failed_tests_with_full_name(project: Path):
    result = subprocess.run(
        ["./gradlew", "clean", "test", "--info"],
        cwd=project,
        capture_output=True,
        text=True
    )
    output = result.stdout + result.stderr

    failed = set()
    current_class = None

    for line in output.splitlines():
        line = line.strip()

        m_full = re.search(r"([a-zA-Z0-9.$_]+)\s+>\s+([^(]+)\(\)\s+FAILED", line)
        if m_full:
            full_name = f"{m_full.group(1)}.{m_full.group(2)}"
            failed.add(full_name)
            current_class = m_full.group(1)
            continue

        m_short = re.search(r">\s+([^(]+)\(\)\s+FAILED", line)
        if m_short and current_class:
            full_name = f"{current_class}.{m_short.group(1)}"
            failed.add(full_name)
            continue

        m_class = re.search(r"Running ([a-zA-Z0-9.$_]+)", line)
        if m_class:
            current_class = m_class.group(1)

    return failed

def load_seeded_bugs_count() -> int:
    if not GROUND_TRUTH_CSV.exists():
        print(f"[FEHLER] Ground Truth CSV nicht gefunden: {GROUND_TRUTH_CSV}")
        return 0
    with open(GROUND_TRUTH_CSV, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        return len(rows) - 1 if rows else 0

def main():
    print("="*100)
    print(" DIFFERENTIAL TESTING – RECALL + PRECISION")
    print(" Recall über gesäte Bugs · Precision über generierte Tests")
    print("="*100)

    if not copy_tests():
        exit(1)

    # 1. Anzahl generierter Tests (aus Quellcode!)
    total_generated_tests = count_generated_tests()

    # 2. Saubere True Positives
    clean_failed = get_failed_tests_with_full_name(CLEAN)
    buggy_failed = get_failed_tests_with_full_name(BUGGY)
    true_positives = buggy_failed - clean_failed
    tp_count = len(true_positives)

    # 3. Gesäte Bugs
    seeded_bugs = load_seeded_bugs_count()
    if seeded_bugs == 0:
        print("Keine gesäten Bugs → Abbruch.")
        return

    # 4. Metriken
    estimated_recall = tp_count / seeded_bugs
    estimated_fns = seeded_bugs - tp_count
    precision = tp_count / total_generated_tests if total_generated_tests > 0 else 0.0

    print(f"\n GESÄTE FAULTS (Ground Truth)                 : {seeded_bugs}")
    print(f" Generierte @Test-Methoden (LLM)                : {total_generated_tests}")
    print(f" True Positive Tests (Clean: Grün | Buggy: Rot) : {tp_count}")
    print()
    print("="*100)
    print(" GESCHÄTZTE METRIKEN")
    print("="*100)
    print(f"  RECALL (Bug-Ebene)          = {tp_count} / {seeded_bugs} = {estimated_recall:.3f} → {estimated_recall*100:5.1f}%")
    print(f"  → Geschätzte FALSE NEGATIVES       = {estimated_fns} Bugs (nicht erkannt)")
    print()
    print(f"  PRECISION (Test-Ebene)      = {tp_count} / {total_generated_tests} = {precision:.3f} → {precision*100:5.1f}%")
    print(f"      → Nur {precision*100:5.1f}% der generierten Tests waren tatsächlich nützlich!")
    print("="*100)

    if true_positives:
        print(f"\n TRUE POSITIVE TESTS ({tp_count}): Diese haben mindestens einen Bug erkannt!")
        for t in sorted(true_positives):
            print(f"   [Success] {t}")
        print("\n   → Bitte manuell zuordnen: Welche gesäten Bugs lösen diese aus?")
    else:
        print("\n KEINE sauberen True Positives → Recall = 0.000")
if __name__ == "__main__":
    main()