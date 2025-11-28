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

BACKUP_ORIGINAL = ROOT / ".original_tests_backup"
BACKUP_FULL = ROOT / ".full_testsuite_backup"
BACKUP_CLEAN_STATE = ROOT / ".project_clean_state_backup"
BACKUP_BUGGY_STATE = ROOT / ".project_buggy_state_backup"

EXEC_BACKUP_ORIGINAL = ROOT / ".jacoco_original.exec"
EXEC_BACKUP_WITH_LLM = ROOT / ".jacoco_with_llm.exec"
JACOCO_DEFAULT_EXEC_REL = Path("build") / "jacoco" / "test.exec"

# Backup & Restore + Cleanup
def backup_project_state():
    if BACKUP_CLEAN_STATE.exists() and BACKUP_BUGGY_STATE.exists():
        return
    print("Sichere ursprünglichen Projektzustand (einmalig)...")
    for proj, backup in [(CLEAN, BACKUP_CLEAN_STATE), (BUGGY, BACKUP_BUGGY_STATE)]:
        if backup.exists():
            shutil.rmtree(backup)
        shutil.copytree(proj, backup, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", "*.log", "__pycache__"))

def restore_project_state():
    print("Stelle ursprünglichen Zustand der Projekte wieder her...")
    for backup, proj in [(BACKUP_CLEAN_STATE, CLEAN), (BACKUP_BUGGY_STATE, BUGGY)]:
        if proj.exists():
            shutil.rmtree(proj)
        shutil.copytree(backup, proj, dirs_exist_ok=True)

def full_cleanup():
    print("\nFühre vollständige Bereinigung durch – ABSOLUT ALLES wird gelöscht...")

    # Alle temporären Dateien und Ordner, die wir je erzeugt haben
    to_delete = [
        BACKUP_ORIGINAL,
        BACKUP_FULL,
        BACKUP_CLEAN_STATE,
        BACKUP_BUGGY_STATE,
        EXEC_BACKUP_ORIGINAL,
        EXEC_BACKUP_WITH_LLM,
    ]

    # Alle dummy*.exec Dateien
    for dummy in ROOT.glob(".dummy*.exec"):
        to_delete.append(dummy)

    # Optional: Auch alle build-Ordner in den Projekten (falls was hängen bleibt)
    for proj in [CLEAN, BUGGY]:
        build_dir = proj / "build"
        if build_dir.exists():
            to_delete.append(build_dir)

    removed = 0
    for path in to_delete:
        if path.exists():
            try:
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=False)
                    print(f"   Gelöscht: Ordner {path.name}/")
                else:
                    path.unlink()
                    print(f"   Gelöscht: Datei  {path.name}")
                removed += 1
            except Exception as e:
                print(f"   FEHLER beim Löschen von {path}: {e}")

    if removed == 0:
        print("   Bereits sauber – nichts zu löschen.")
    else:
        print(f"   Insgesamt {removed} temporäre Elemente entfernt – Repo 100% sauber!")

def ensure_test_backups():
    if not BACKUP_ORIGINAL.exists():
        src = CLEAN / "src/test/java"
        if src.exists():
            print("Sichere Original-Tests → .original_tests_backup")
            shutil.copytree(src, BACKUP_ORIGINAL, dirs_exist_ok=True)
    if not BACKUP_FULL.exists():
        src = BUGGY / "src/test/java"
        if src.exists():
            print("Sichere volle Testsuite (inkl. LLM) → .full_testsuite_backup")
            shutil.copytree(src, BACKUP_FULL, dirs_exist_ok=True)

def set_tests(proj: Path, source: Path):
    target = proj / "src/test/java"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, dirs_exist_ok=True)
    (proj / "build").mkdir(exist_ok=True)

# Testlauf + Coverage + JUnit-Results
def run_tests_and_capture_coverage(proj: Path, backup_exec: Path) -> tuple[Set[str], Set[str]]:
    print(f"  Running: ./gradlew clean test  →  Coverage → {backup_exec.name}")
    subprocess.run(["./gradlew", "clean", "test", "--quiet"], cwd=proj, capture_output=True, text=True)

    default_exec = proj / JACOCO_DEFAULT_EXEC_REL
    if not default_exec.exists():
        print(f"   WARNING: KEINE test.exec gefunden unter {default_exec}")
        return set(), set()

    shutil.copy2(default_exec, backup_exec)
    print(f"   Coverage gesichert → {backup_exec.name} ({default_exec.stat().st_size:,} Bytes)")

    failed: Set[str] = set()
    executed: Set[str] = set()
    xml_dir = proj / "build" / "test-results" / "test"

    if xml_dir.exists():
        for xml_file in xml_dir.rglob("TEST-*.xml"):
            try:
                tree = ET.parse(xml_file)
                for tc in tree.getroot().iter("testcase"):
                    classname = tc.get("classname", "")
                    method = re.split(r"[\[\(]", tc.get("name", ""))[0].strip()
                    full_name = f"{classname}.{method}"
                    executed.add(full_name)
                    if tc.find("failure") is not None or tc.find("error") is not None:
                        failed.add(full_name)
            except Exception as e:
                print(f"     Warnung: Konnte {xml_file.name} nicht parsen: {e}")
    return failed, executed

def get_coverage_from_report(proj: Path) -> float:
    report = proj / "build" / "reports" / "jacoco" / "test" / "jacocoTestReport.xml"
    if not report.exists():
        return 0.0
    try:
        tree = ET.parse(report)
        missed = covered = 0
        for counter in tree.getroot().findall(".//counter[@type='LINE']"):
            missed += int(counter.get("missed", 0))
            covered += int(counter.get("covered", 0))
        total = missed + covered
        return (covered / total * 100) if total > 0 else 0.0
    except Exception:
        return 0.0

# Hauptlogik
def main():
    print("=" * 100)
    print(" LLM TEST EVALUATION")
    print("=" * 100)

    backup_project_state()
    restore_project_state()
    ensure_test_backups()

    try:
        print("\nPhase 1: Originaltests auf Clean")
        set_tests(CLEAN, BACKUP_ORIGINAL)
        failed_A, executed_A = run_tests_and_capture_coverage(CLEAN, EXEC_BACKUP_ORIGINAL)
        subprocess.run(["./gradlew", "jacocoTestReport", "--quiet"], cwd=CLEAN, check=False)
        cov_original = get_coverage_from_report(CLEAN)

        print("\nPhase 2: Originaltests auf Buggy")
        set_tests(BUGGY, BACKUP_ORIGINAL)
        failed_B, _ = run_tests_and_capture_coverage(BUGGY, ROOT / ".dummy_original_buggy.exec")

        print("\nPhase 3: Volle Suite auf Clean")
        set_tests(CLEAN, BACKUP_FULL)
        failed_C, executed_C = run_tests_and_capture_coverage(CLEAN, EXEC_BACKUP_WITH_LLM)
        subprocess.run(["./gradlew", "jacocoTestReport", "--quiet"], cwd=CLEAN, check=False)
        cov_with_llm = get_coverage_from_report(CLEAN)

        print("\nPhase 4: Volle Suite auf Buggy")
        set_tests(BUGGY, BACKUP_FULL)
        failed_D, executed_D = run_tests_and_capture_coverage(BUGGY, ROOT / ".dummy_full_buggy.exec")

        llm_tests = executed_C - executed_A
        if not llm_tests:
            print("\nERROR: Keine LLM-Tests erkannt!")
            return

        # === KORREKTE KLASSIFIZIERUNG ===
        broken_tests = failed_C & llm_tests
        good_candidates = llm_tests - broken_tests
        already_detected = good_candidates & failed_B
        true_positives = good_candidates & failed_D
        false_positives = broken_tests
        stable_green = good_candidates - failed_D
        anti_tests = broken_tests - failed_D

        seeded = 0
        if GROUND_TRUTH.exists():
            with open(GROUND_TRUTH, newline='', encoding='utf-8') as f:
                seeded = len(list(csv.reader(f))) - 1

        total_llm = len(llm_tests)
        precision = len(true_positives) / total_llm if total_llm else 0.0
        recall = len(true_positives) / seeded if seeded else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        # === KOMPAKTE ZUSAMMENFASSUNG ===
        print("\n" + "="*80)
        print(" FINAL RESULTS – VOLLTAXONOMIE")
        print("="*80)
        print(f" LLM-Tests gesamt                  : {total_llm:4d}")
        print(f" ├─ True Positives (neu)           : {len(true_positives):4d}   ← Neue Bug-Detektoren")
        print(f" ├─ Already detected (redundant)   : {len(already_detected):4d}   ← Verstehen das System, aber kein Gewinn")
        print(f" ├─ False Positives (broken)       : {len(false_positives):4d}")
        print(f" │  ├─ davon ANTI-TESTS            : {len(anti_tests):4d}   ← HOCHGEFÄHRLICH! Nur grün durch Bugs")
        print(f" │  └─ davon klassisch kaputt      : {len(false_positives - anti_tests):4d}")
        print(f" └─ Stable Green (harmlos)         : {len(stable_green):4d}   ← Gute Coverage, sicher")
        print(f" Precision (nur neue TPs)          : {precision:6.1%}")
        print(f" Recall (von {seeded} seeded Bugs) : {recall:6.1%}")
        print(f" F1-Score                          : {f1:.3f}")
        print(f" Coverage Gain                     : {cov_with_llm - cov_original:+5.1f} pp")

        # === DETAILAUSGABE NUR BEI VORHANDENSEIN ===
        if true_positives:
            print("\nTrue Positives – neue Bug-Detektoren:")
            for t in sorted(true_positives):
                print(f"   • {t}")

        if already_detected:
            print(f"\nRedundante Bug-Detektoren (already detected by original tests):")
            for t in sorted(already_detected):
                print(f"   • {t}")

        if anti_tests:
            print(f"\nHOCHGEFÄHRLICH: ANTI-TESTS (rot auf Clean, GRÜN auf Buggy!)")
            print("   → Diese Tests werden nur durch Bugs 'gerettet' – absolut toxisch!")
            for t in sorted(anti_tests):
                print(f"   • {t}")

        if false_positives - anti_tests:
            print(f"\nKlassische kaputte Tests (rot auf Clean + Buggy):")
            for t in sorted(false_positives - anti_tests):
                print(f"   • {t}")

        if stable_green:
            print(f"\nCoverage-Potential: Stable Green Tests (grün auf beiden):")
            for t in sorted(stable_green):
                print(f"   • {t}")

    finally:
        restore_project_state()
        print("\nProjekte zurückgesetzt.")
        full_cleanup()

    print("\n" + "="*100)
    print("FERTIG.")
    print("="*100)

if __name__ == "__main__":
    main()