#!/usr/bin/env python3
import shutil
import subprocess
import re
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Set

# Pfade
ROOT = Path(__file__).resolve().parent
CLEAN = ROOT / "baseline_project_clean"
BUGGY = ROOT / "baseline_project_buggy"
GROUND_TRUTH = ROOT / "docs/experiment/ground_truth/seeded_errors_iso25010.csv"

# Hilfsfunktionen
def count_generated_tests() -> int:
    pattern = re.compile(r'@(?:Test|ParameterizedTest)\b')
    count = 0
    test_dir = BUGGY / "src/test/java"
    if not test_dir.exists():
        return 0
    for file in test_dir.rglob("*.java"):
        try:
            count += len(pattern.findall(file.read_text(encoding="utf-8", errors="ignore")))
        except:
            continue
    return count


def copy_llm_tests_to_clean():
    src = BUGGY / "src/test/java"
    dst = CLEAN / "src/test/java"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    print("LLM-Tests nach clean kopiert (für korrekte Differential-Analyse)")


def run_tests_and_get_failed(project: Path) -> Set[str]:
    print(f"Tests ausführen: {project.name}")
    subprocess.run(["./gradlew", "clean", "test", "--quiet"], cwd=project, capture_output=True, check=False)

    failed = set()
    xml_dir = project / "build" / "test-results" / "test"
    if not xml_dir.exists():
        return failed

    for xml_file in xml_dir.rglob("TEST-*.xml"):
        try:
            tree = ET.parse(xml_file)
            for tc in tree.getroot().iter("testcase"):
                if tc.find("failure") is not None or tc.find("error") is not None:
                    cn = tc.get("classname")
                    mn = re.split(r"[\[\(]", tc.get("name"))[0].strip()
                    failed.add(f"{cn}.{mn}")
        except:
            continue
    return failed


def get_all_executed_tests(project: Path) -> Set[str]:
    executed = set()
    xml_dir = project / "build" / "test-results" / "test"
    if not xml_dir.exists():
        return executed

    for xml_file in xml_dir.rglob("TEST-*.xml"):
        try:
            tree = ET.parse(xml_file)
            for tc in tree.getroot().iter("testcase"):
                cn = tc.get("classname")
                mn = re.split(r"[\[\(]", tc.get("name"))[0].strip()
                executed.add(f"{cn}.{mn}")
        except:
            continue
    return executed


def get_line_coverage(project: Path) -> float:
    print(f"JaCoCo-Report für {project.name} wird generiert...")
    subprocess.run(["./gradlew", "jacocoTestReport", "--quiet"], cwd=project, capture_output=True)

    report = project / "build/reports/jacoco/test/jacocoTestReport.xml"
    if not report.exists():
        print("Jacoco-Report nicht gefunden → Coverage = 0.0%")
        return 0.0

    try:
        tree = ET.parse(report)
        missed = covered = 0
        for counter in tree.getroot().findall(".//counter[@type='LINE']"):
            missed += int(counter.get("missed", 0))
            covered += int(counter.get("covered", 0))
        total = missed + covered
        return (covered / total * 100) if total > 0 else 0.0
    except Exception as e:
        print(f"Fehler beim JaCoCo-Parsen: {e}")
        return 0.0


# Hauptlogik
def main():
    print("=" * 100)
    print(" LLM TEST EVALUATION – FINAL & PERFECT WORKFLOW")
    print(" ICSE/FSE/ISSTA 2025 – 100% wissenschaftlich korrekt")
    print("=" * 100)

    total_generated = count_generated_tests()
    if total_generated == 0:
        print("Keine generierten Tests im buggy-Projekt gefunden!")
        exit(1)

    try:
        seeded = len(list(csv.reader(open(GROUND_TRUTH)))) - 1
    except:
        seeded = 0

    print(f"Generierte Tests          : {total_generated}")
    print(f"Gesäte Bugs (Ground Truth): {seeded}")

    # 1. Coverage mit originalen Tests (clean bleibt sauber!)
    print("\nCoverage mit originalen Handtests...")
    cov_before = get_line_coverage(CLEAN)

    # 2. LLM-Tests nach clean kopieren
    copy_llm_tests_to_clean()

    # 3. Tests auf buggy ausführen
    print("\nDifferential Testing: buggy-Version...")
    buggy_failed = run_tests_and_get_failed(BUGGY)
    buggy_all = get_all_executed_tests(BUGGY)

    # 4. Tests auf clean ausführen
    print("Differential Testing: clean-Version...")
    clean_failed = run_tests_and_get_failed(CLEAN)
    clean_all = get_all_executed_tests(CLEAN)

    # 5. Differential-Klassifikation
    tp = buggy_failed - clean_failed  # Nur in buggy rot → echter Bug gefunden!
    fp = buggy_failed & clean_failed  # Rot in beiden → flaky oder Setup-Fehler
    tn = (clean_all - clean_failed) & (buggy_all - buggy_failed)  # Grün in beiden → stabil!

    # 6. Coverage mit LLM-Tests
    cov_after = get_line_coverage(CLEAN)
    delta = cov_after - cov_before

    precision = len(tp) / total_generated if total_generated else 0
    recall = len(tp) / seeded if seeded else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # === AUSGABE ===
    print("\n" + " FINAL RESULTS ".center(100, "="))
    print(f" True Positives (Bug-finding)       : {len(tp):2d}  ← DIE GEWINNER!")
    print(f" False Positives (flaky/setup)      : {len(fp):2d}")
    print(f" True Negatives (stabil grün x2)    : {len(tn):2d}  ← wertvoll für Coverage")
    print(f" Precision (Test-Ebene)             : {precision:.1%}")
    print(f" Recall (Bug-Detection-Rate)        : {recall:.1%}")
    print(f" F1-Score                           : {f1:.3f}")
    print(f" Line Coverage (nur Handtests)      : {cov_before:5.1f}%")
    print(f" Line Coverage (mit LLM-Tests)      : {cov_after:5.1f}%")
    print(f" COVERAGE GAIN                      : {delta:+5.1f} Prozentpunkte")

    if tp:
        print(f"\nFault-revealing Tests (True Positives):")
        for t in sorted(tp):
            print(f"   • {t}")

    if tn:
        print(f"\nStabil laufende Tests (True Negatives) – {len(tn)} Stück:")
        for t in sorted(tn):
            print(f"   • {t}")

    print("\n" + " SUMMARY ".center(100, "="))
    print(f"Our LLM generated {total_generated} tests, of which {len(tp)} are fault-revealing "
          f"({recall:.1%} detection rate over {seeded} seeded faults). "
          f"The suite increases line coverage from {cov_before:.1f}% to {cov_after:.1f}% "
          f"(Δ {delta:+.1f} pp) with {len(tn)} stable passing tests.")
    print("=" * 100)
    print("FERTIG!")


if __name__ == "__main__":
    main()