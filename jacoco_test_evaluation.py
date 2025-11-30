#!/usr/bin/env python3
import sys
import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import xml.etree.ElementTree as ET

BASE_DIR = Path("/home/dbe/projects/llm-code-quality-experiment/docs/experiment/results")
EXPERIMENT = sys.argv[1].strip("/") if len(sys.argv) > 1 else None

if not EXPERIMENT:
    print("Aufruf: python test_analyzer_strict_final.py <experiment-name>")
    sys.exit(1)

base = BASE_DIR / EXPERIMENT
buggy_dir = base / "buggy"
clean_dir = base / "clean"

if not buggy_dir.exists() or not clean_dir.exists():
    print(f"Fehler: Ordner fehlen: {base}")
    sys.exit(1)

print(f"\nTEST ANALYZER STRICT FINAL – {EXPERIMENT}")
print("STRICT MODE + LOGISCHE GRUPPIERUNG VON PARAMETERIZED TESTS")
print("="*100)

# 1. JUnit XML parsen
def parse_tests(dir_path: Path) -> tuple[set[str], set[str]]:
    failed = set()
    executed = set()
    reports = dir_path / "build" / "test-results" / "test"
    if not reports.exists():
        print(f"Keine test-results in {dir_path}")
        return failed, executed

    for xml in reports.rglob("TEST-*.xml"):
        try:
            tree = ET.parse(xml)
            for tc in tree.getroot().findall(".//testcase"):
                cls = tc.get("classname")
                name = tc.get("name")
                if not cls or not name:
                    continue
                full = f"{cls}#{name}"
                executed.add(full)
                if tc.find("failure") is not None or tc.find("error") is not None:
                    failed.add(full)
        except Exception:
            continue
    return failed, executed

clean_failed, clean_executed = parse_tests(clean_dir)
buggy_failed, buggy_executed = parse_tests(buggy_dir)


# 2. LOGISCHE GRUPPIERUNG (ParameterizedTest → 1 logischer Test)
def normalize_test_name(full_name: str) -> str:
    cls, method = full_name.split("#", 1)
    method = re.sub(r"\[.*\]$", "", method)
    method = re.sub(r"\s*\([^)]*\)$", "", method)
    method = re.sub(r"^\s*\d+:\s*", "", method)
    method = re.sub(r"\s+→.*$", "", method)
    return f"{cls}#{method.strip()}"

print("\nGruppierung von Parameterized/DisplayName Tests...")

logical_groups = defaultdict(lambda: {
    "instances": set(),
    "buggy_failed": False,
    "clean_passed_all": True,
    "has_buggy": False,
    "has_clean": False
})

all_tests = buggy_failed | clean_failed | buggy_executed | clean_executed
for test in all_tests:
    logical = normalize_test_name(test)
    g = logical_groups[logical]
    g["instances"].add(test)

    if test in buggy_failed:          g["buggy_failed"] = True
    if test in buggy_executed:        g["has_buggy"] = True
    if test in clean_executed:        g["has_clean"] = True
    if test in clean_failed:          g["clean_passed_all"] = False

# Klassifizierung
true_positives = set()
false_positives = set()
dangerous_regressions = set()
always_passing = set()

for logical, d in logical_groups.items():
    if not (d["has_buggy"] or d["has_clean"]):
        continue

    if d["buggy_failed"] and d["clean_passed_all"] and d["has_clean"]:
        true_positives.add(logical)
    elif d["buggy_failed"] and not d["clean_passed_all"] and d["has_clean"]:
        false_positives.add(logical)
    elif not d["buggy_failed"] and d["has_buggy"] and not d["clean_passed_all"] and d["has_clean"]:
        dangerous_regressions.add(logical)
    elif d["has_buggy"] or d["has_clean"]:
        always_passing.add(logical)

print(f"Logische Tests gesamt:          {len(logical_groups):3d}")
print(f"True Positives (entdupliziert): {len(true_positives):3d}")
print(f"False Positives:                {len(false_positives):3d}")
print(f"Gefährliche Regressionen:       {len(dangerous_regressions):3d}")
print(f"Immer grün:                     {len(always_passing):3d}")

print("\n" + "="*120)
print("VOLLSTÄNDIGE INSTANZEN DER TRUE POSITIVES (genau so, wie JUnit sie sieht):")
print("="*120)
for logical in sorted(true_positives):
    print(f"\nLogischer Test → {logical}")
    for full_name in sorted(logical_groups[logical]["instances"]):
        status = "ROT in buggy" if full_name in buggy_failed else "grün in buggy"
        print(f"   → {full_name}   [{status}]")
print("="*120)

# 3. JaCoCo Coverage
def find_jacoco(root: Path) -> Path | None:
    for p in [
        root / "build" / "reports" / "jacoco" / "test" / "html",
        root / "build" / "reports" / "jacoco" / "testHtml" / "html",
        root / "build" / "reports" / "jacoco" / "html",
    ]:
        if p.exists():
            return p
    return None

jacoco_dir = find_jacoco(buggy_dir) or find_jacoco(clean_dir)
coverage_by_test = defaultdict(list)

if jacoco_dir:
    print(f"JaCoCo gefunden: {jacoco_dir.relative_to(BASE_DIR)}")
    for html_file in jacoco_dir.rglob("*.java.html"):
        content = html_file.read_text(encoding="utf-8", errors="ignore")

        rel_parts = html_file.relative_to(jacoco_dir).parts
        class_name = ".".join(rel_parts[:-1] + (html_file.stem,))

        covered_lines = [
            int(m.group(1)) for line in content.splitlines()
            if (m := re.search(r'id="L(\d+)"', line)) and ('fc' in line or 'pc' in line)
        ]
        if not covered_lines:
            continue

        test_titles = re.findall(r'title="([^"]+)"\s+class="(fc|pc)"', content)
        lines_sorted = sorted(covered_lines)

        for title in {t.strip() for t in test_titles}:
            entry = {"class": class_name, "lines": lines_sorted, "count": len(lines_sorted)}

            # Viele Varianten für perfektes Matching
            variants = [
                title,
                title.split("[")[0].strip(),
                re.sub(r'\s*\([^)]*\)', '', title),
                re.sub(r'\s+.*$', '', title),
                title.split(" (")[0],
                normalize_test_name(f"X#{title}").split("#", 1)[1],
            ]
            for v in set(variants):
                if v:
                    coverage_by_test[v].append(entry)
else:
    print("Kein JaCoCo Report gefunden")

# 4. Coverage für logischen Test holen
def get_best_coverage(logical_name: str) -> dict:
    candidates = [
        logical_name,
        logical_name.split("#", 1)[1],
    ]
    for key in candidates:
        if key in coverage_by_test and coverage_by_test[key]:
            entries = coverage_by_test[key]
            return {
                "source": key,
                "total": sum(e["count"] for e in entries),
                "classes": len({e["class"] for e in entries}),
                "details": entries[:8]
            }
    return {"source": None, "total": 0, "classes": 0, "details": []}

# 5. Report erzeugen
md = [
    f"# TEST ANALYZER FINAL – {EXPERIMENT}",
    f"Generiert: {datetime.now():%Y-%m-%d %H:%M:%S}",
    "",
    "**Logische Gruppierung aktiv** → ParameterizedTests zählen nur einmal!",
    "",
    "## Zusammenfassung",
    f"- **True Positives** (Bug erkannt, entdupliziert): **{len(true_positives)}**",
    f"- False Positives (Test kaputt): **{len(false_positives)}**",
    f"- Gefährliche Regressionen Regressionen: **{len(dangerous_regressions)}**",
    f"- Immer grün (Coverage-Potential): **{len(always_passing)}**",
    "",
]

def section(title: str, tests: set, emoji: str):
    if not tests:
        md.extend([f"## " + emoji + " " + title, "_Keine_", ""])
        return
    md.append(f"## {emoji} {title} ({len(tests)})")
    for logical in sorted(tests):
        n = len(logical_groups[logical]["instances"])
        note = f" ({n} Instanzen)" if n > 1 else ""
        cls, method = logical.split("#", 1)
        cov = get_best_coverage(logical)
        md.append(f"### `{method}`{note}")
        md.append(f"- Klasse: `{cls}`")
        if cov["total"] > 0:
            md.append(f"- Coverage: **{cov['total']} Zeilen** in {cov['classes']} Klassen")
            for d in cov["details"]:
                preview = ", ".join(map(str, d["lines"][:12]))
                more = f" ... (+{len(d['lines'])-12})" if len(d['lines']) > 12 else ""
                md.append(f"  → `{d['class']}`: {preview}{more}")
        else:
            md.append("- Coverage: _nicht gefunden_ (häufig bei @ParameterizedTest)")
        md.append("")

section("TP – Fault wird erkannt!", true_positives, "Bug")
section("FP – Test ist kaputt", false_positives, "Test kaputt")
section("FP(GEFÄHRLICH) – Regression durch Fix", dangerous_regressions, "Regression")
section("Immer grün – Coverage-Potential", always_passing, "Grün")

# Speichern
md_path = base / "TEST_ANALYZER_FINAL.md"
json_path = base / "TEST_ANALYZER_FINAL.json"

md_path.write_text("\n".join(md), encoding="utf-8")

json_data = {
    "experiment": EXPERIMENT,
    "generated": datetime.now().isoformat(),
    "logical_grouping": True,
    "true_positives": sorted(true_positives),
    "false_positives": sorted(false_positives),
    "dangerous_regressions": sorted(dangerous_regressions),
    "always_passing": sorted(always_passing),
    "total_logical_tests": len(logical_groups),
    "coverage": {t: get_best_coverage(t) for t in (true_positives | always_passing)}
}

json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")

print("="*100)
print("FERTIG!")
print(f"→ {md_path}")
print(f"→ {json_path}")
if true_positives:
    print(f"\nDer Bug wird von {len(true_positives)} verschiedenen logischen Test(s) erkannt!")
if dangerous_regressions:
    print("REGRESSIONEN ERKANNT")
print("="*100)