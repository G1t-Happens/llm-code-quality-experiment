#!/usr/bin/env python3
# count_compilable_tests_strict_with_total_tests.py
# → Zeigt dir: Wie viele @Test-Methoden hat die KI wirklich generiert?
# → Und welche Klassen sind der Grund, dass nicht alles kompilierbar ist?

import shutil
import subprocess
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
GENERATED = BASE / "generated_tests"
PROJECT = BASE / "baseline_project_clean"
SRC_TEST = PROJECT / "src" / "test" / "java"

TEST_PATTERN = re.compile(
    r'^\s*@(?:org\.junit\.jupiter\.api\.)?(Test|ParameterizedTest|RepeatedTest|TestFactory|TestTemplate)\b',
    re.MULTILINE
)

def count_tests_in_file(file_path: Path) -> int:
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return len(TEST_PATTERN.findall(content))
    except Exception as e:
        print(f"  Warnung: Konnte {file_path.name} nicht lesen: {e}")
        return 0

def clean():
    if SRC_TEST.exists():
        shutil.rmtree(SRC_TEST)
    SRC_TEST.mkdir(parents=True, exist_ok=True)

def try_compile() -> tuple[bool, str]:
    result = subprocess.run(
        ["./gradlew", "compileTestJava", "--quiet", "--stacktrace"],
        cwd=PROJECT,
        capture_output=True,
        text=True
    )
    full_output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, full_output

def clean_test_dir():
    if SRC_TEST.exists():
        shutil.rmtree(SRC_TEST)
    SRC_TEST.mkdir(parents=True, exist_ok=True)

def deploy_all_tests():
    """Kopiert ALLE generierten Tests ins echte Projekt – bereit zum Fixen!"""
    print("\nKopiere alle generierten Tests ins baseline_project_clean → du kannst jetzt direkt fixen!")
    clean_test_dir()
    for src in GENERATED.rglob("*.java"):
        rel = src.relative_to(GENERATED)
        dest = SRC_TEST / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    print(f"→ {len(list(GENERATED.rglob('*.java')))} Dateien erfolgreich deployt nach:")
    print(f"  {SRC_TEST}")
    print("  Jetzt einfach ausführen:")
    print("     ./gradlew compileTestJava")
    print("  oder im IDE öffnen und rote Stellen auskommentieren/fixen")

def main():
    java_files = sorted(GENERATED.rglob("*.java"))
    total_files = len(java_files)

    if total_files == 0:
        print("Keine generierten .java-Dateien gefunden!")
        return

    print("Zähle alle generierten Testmethoden (auch in syntaktisch kaputten Klassen)...\n")

    total_tests = 0
    tests_per_file = {}
    for src in java_files:
        rel = src.relative_to(GENERATED)
        count = count_tests_in_file(src)
        tests_per_file[str(rel)] = count
        total_tests += count
        print(f"  {rel} → {count} Testmethoden")

    print(f"\nInsgesamt generierte @Test-Methoden: {total_tests}")
    print(f"Generierte Dateien: {total_files}")
    print("\nStarte strenge Kompilierbarkeitsprüfung (1 Datei nach der anderen)...\n")

    clean()
    compilable_files = 0
    broken_files = []

    for i, src in enumerate(java_files, 1):
        rel = src.relative_to(GENERATED)
        dest = SRC_TEST / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

        print(f"[{i:>3}/{total_files}] {rel}", end=" ... ")

        success, output = try_compile()

        if success:
            print("KOMPILIERT")
            compilable_files += 1
        else:
            print("KAPUTT")
            broken_files.append((str(rel), tests_per_file[str(rel)], output))

        # Aufräumen
        dest.unlink(missing_ok=True)
        try:
            dest.parent.rmdir()
        except OSError:
            pass

    # ==============================
    # DEIN ARBEITSBERICHT – perfekt für den manuellen Rescue
    # ==============================
    print("\n" + "="*85)
    print("           BRUTALE WAHRHEIT – WAS HAT DIE KI WIRKLICH GELIEFERT?")
    print("="*85)
    print(f"  Generierte Testdateien          : {total_files}")
    print(f"  Generierte @Test-Methoden      : {total_tests}   ← DAS ist deine 100%-Basis!")
    print(f"  Direkt kompilierbare Dateien   : {compilable_files}/{total_files}")
    print(f"  Direkt kompilierbare Tests     : {sum(tests_per_file[f] for f in tests_per_file if f not in [b[0] for b in broken_files])}")
    print()
    print(f"  Kaputte Dateien (Compiler-Blocker): {len(broken_files)}")
    print(f"  Davon betroffene Testmethoden     : {sum(b[1] for b in broken_files)}")
    print()
    print("Diese Klassen musst du jetzt manuell retten (auskommentieren/fixen):")
    print("-" * 85)

    for filename, test_count, error_output in broken_files:
        print(f"\n{filename}")
        print(f"   → Enthält {test_count} @Test-Methoden (werden aktuell alle blockiert)")
        print("   → Compiler-Fehler (wichtigste Zeilen):")
        lines = [l.rstrip() for l in error_output.splitlines() if l.strip() and ("error:" in l or "cannot find symbol" in l or "incompatible types" in l)]
        for line in lines[-20:]:
            print(f"     {line}")
        if len(lines) > 20:
            print("     ... (weitere Fehler weggelassen)")

    print("\n" + "-"*85)
    print("Nächster Schritt für dich:")
    print("  → Öffne jede kaputte Datei,")
    print("  → Kommentiere die fehlerhaften Tests aus oder fix sie minimal,")
    print("  → Zähle, wie viele von den ursprünglichen", total_tests, "Tests du retten konntest.")
    print("  → Dann hast du deine echte ‚Rettungsrate‘: z.B. 47/53 = 88.7%")
    print("="*85)

    # === FINALER SCHRITT: DEPLOY ===
    deploy_all_tests()

    print("\n" + "="*90)
    print("   DU KANNST JETZT SOFORT LOSLEGEN:")
    print("   1. cd baseline_project_clean")
    print("   2. ./gradlew compileTestJava    ← siehst alle Fehler live")
    print("   3. Oder IDE öffnen → alles rot leuchtend → auskommentieren/fixen")
    print("   4. Am Ende: zähle die übrigen @Test-Methoden → deine echte Qualitätsrate!")
    print("="*90)

if __name__ == "__main__":
    main()