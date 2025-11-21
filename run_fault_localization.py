#!/usr/bin/env python3
import json
import time
import os
import hashlib
import argparse
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Any, Dict

import dotenv
from pydantic import BaseModel, Field
import requests
from openai import OpenAI, APIError
from openai import Timeout as OpenAITimeout
from openai import RateLimitError as OpenAIRateLimitError

# ----------------------------- Constants & Paths -----------------------------
BASE_DIR = Path(__file__).parent.resolve()

# Default paths
CODE_FILE = BASE_DIR / "docs" / "experiment" / "code_under_test" / "extracted_code.txt"
SYSTEM_PROMPT_FILE = BASE_DIR / "docs" / "experiment" / "llm_config" / "system_prompt.txt"
SYSTEM_PROMPT_TEST_FILE = BASE_DIR / "docs" / "experiment" / "llm_config" / "system_prompt_test.txt"
USER_PROMPT_FILE = BASE_DIR / "docs" / "experiment" / "llm_config" / "user_prompt.txt"
ENV_FILE = BASE_DIR / "docs" / "experiment" / "llm_config" / ".env"
RESULTS_DIR = BASE_DIR / "docs" / "experiment" / "results"
GENERATED_TESTS_DIR = BASE_DIR / "baseline_project" / "src" / "test" / "java"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)

dotenv.load_dotenv(ENV_FILE)

# ----------------------------- Environment -----------------------------
PROVIDER = os.getenv("PROVIDER", "grok").lower()
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "32768"))
O1_MAX_COMPLETION_TOKENS = int(os.getenv("O1_MAX_COMPLETION_TOKENS", "32768"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "600"))
TOP_P = float(os.getenv("TOP_P", "0.90"))
DEBUG = os.getenv("DEBUG", "0") == "1"

# Provider config
if PROVIDER == "grok":
    API_KEY = os.getenv("GROK_API_KEY")
    MODEL = os.getenv("GROK_MODEL", "grok-4-fast-non-reasoning")
    API_BASE = os.getenv("GROK_API_BASE", "https://api.x.ai/v1").rstrip("/")
elif PROVIDER == "openai":
    API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
    API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
else:
    raise ValueError(f"Ungültiger PROVIDER: {PROVIDER}. Muss 'grok' oder 'openai' sein.")

if not API_KEY:
    raise ValueError(f"{PROVIDER.upper()}_API_KEY fehlt in der .env!")

# ----------------------------- Pydantic Models (nur für Fault-Mode) -----------------------------
class SeededBug(BaseModel):
    filename: str
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    severity: str = Field(..., pattern="^(critical|high|medium|low)$")
    error_description: str

class BugList(BaseModel):
    bugs: List[SeededBug]

# ----------------------------- File Utilities -----------------------------
def load_file(file_path: Path) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")
    return file_path.read_text(encoding="utf-8").strip()

def load_code() -> str:
    code = CODE_FILE.read_text(encoding="utf-8")
    md5 = hashlib.md5(code.encode()).hexdigest()
    print(f"Code geladen: {len(code):,} Zeichen | MD5: {md5}")
    return code

# ----------------------------- TEST GENERATION  -----------------------------
def clear_generated_tests():
    """Löscht alle generierten Tests – für saubere Läufe"""
    if GENERATED_TESTS_DIR.exists():
        print(f"Lösche alten Test-Ordner: {GENERATED_TESTS_DIR}")
        shutil.rmtree(GENERATED_TESTS_DIR)
    GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)


def resolve_test_path(marker_path: str) -> Path:
    path = Path(marker_path.strip())

    # Extrahiere nur den Teil ab "com/llmquality/baseline/..."
    try:
        # Finde den Index von "com" – das ist der sichere Anker
        com_index = list(path.parts).index("com")
        relative_parts = path.parts[com_index:]
    except ValueError:
        # Fallback: suche nach "baseline" oder nimm einfach alles ab dem letzten "java"
        try:
            java_index = [i for i, p in enumerate(path.parts) if p == "java"][-1]
            relative_parts = path.parts[java_index + 1:]
        except IndexError:
            raise ValueError(f"Kann Package nicht finden in Pfad: {marker_path}")

    test_path = GENERATED_TESTS_DIR.joinpath(*relative_parts)

    if not test_path.name.endswith("Test.java"):
        stem = test_path.stem
        if not stem.endswith("Test"):
            stem += "Test"
        test_path = test_path.with_name(f"{stem}.java")

    test_path.parent.mkdir(parents=True, exist_ok=True)
    return test_path

    relative = path.parts[idx + 1 :]
    test_path = GENERATED_TESTS_DIR.joinpath(*relative)

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
        print("Leerer Pfad nach Parsing → überspringe")
        return

    print(f"Versuche zu speichern: {path_str}")

    try:
        test_path = resolve_test_path(path_str)
    except ValueError as e:
        print(f"PARSE-FEHLER bei: {path_str}")
        print(f"   Grund: {e}")
        print(f"   → Test wird übersprungen\n")
        return
    except Exception as e:
        print(f"UNERWARTETER FEHLER bei: {path_str}")
        print(f"   {type(e).__name__}: {e}")
        print(f"   → Test wird übersprungen\n")
        return

    # Package ableiten
    try:
        p = Path(path_str)
        com_idx = list(p.parts).index("com")
        package = ".".join(p.parts[com_idx:-1])
    except Exception as e:
        print(f"Package konnte nicht abgeleitet werden für {path_str} → fallback")
        package = "com.llmquality.baseline"

    java_content = content.strip()
    if not java_content.startswith("package "):
        java_content = f"package {package};\n\n{java_content}"

    test_path.write_text(java_content, encoding="utf-8")
    print(f"Test gespeichert → {test_path}\n")
    return True

# ----------------------------- LLM Clients -----------------------------
class GrokClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        })

    def chat(self, messages: List[Dict], use_structured: bool = False, schema=None):
        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "max_tokens": MAX_TOKENS,
        }
        if use_structured and schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "bug_list",
                    "strict": True,
                    "schema": schema.model_json_schema()
                }
            }

        resp = self.session.post(f"{API_BASE}/chat/completions", json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def close(self):
        self.session.close()

# ----------------------------- Core Logic -----------------------------
def run_fault_localization(code: str):
    system_prompt = load_file(SYSTEM_PROMPT_FILE)
    user_prompt = load_file(USER_PROMPT_FILE).format(code=code)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    print(f"🔍 Starte statische Fault Localization mit {PROVIDER.upper()} ({MODEL})...")
    if PROVIDER == "grok":
        client = GrokClient()
        try:
            data = client.chat(messages, use_structured=True, schema=BugList)
        finally:
            client.close()
    else:
        client = OpenAI(api_key=API_KEY, base_url=API_BASE, timeout=REQUEST_TIMEOUT)
        data = client.chat.completions.parse(
            model=MODEL,
            messages=messages,
            response_format=BugList,
            temperature=TEMPERATURE,
            max_completion_tokens=MAX_TOKENS,
        ).model_dump()

    raw_content = data["choices"][0]["message"]["content"]
    parsed = BugList.model_validate(json.loads(raw_content))
    bugs = [bug.model_dump() for bug in parsed.bugs]

    # Save results
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"{PROVIDER}_fault"
    raw_file = RESULTS_DIR / f"{prefix}_raw_{ts}.json"
    bugs_file = RESULTS_DIR / f"{prefix}_bugs_{ts}.json"
    raw_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    bugs_file.write_text(json.dumps(bugs, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n✅ Fault Localization abgeschlossen! {len(bugs)} Bug(s) gefunden.")
    print(f"   Raw → {raw_file}")
    print(f"   Bugs → {bugs_file}\n")

def run_test_generation(code: str, clear_first: bool):
    if clear_first:
        clear_generated_tests()

    system_prompt = load_file(SYSTEM_PROMPT_TEST_FILE)
    user_prompt = load_file(USER_PROMPT_FILE).format(code=code)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt + "\n\nGeneriere vollständige JUnit 5 Testklassen mit korrekten Dateimarkern."}
    ]

    print(f"Starte Testgenerierung mit {PROVIDER.upper()} ({MODEL})...")

    if PROVIDER == "grok":
        client = GrokClient()
        try:
            data = client.chat(messages, use_structured=False)
        finally:
            client.close()
    else:
        client = OpenAI(api_key=API_KEY, base_url=API_BASE, timeout=REQUEST_TIMEOUT)
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_completion_tokens=MAX_TOKENS,
        )
        data = completion.model_dump()

    content = data["choices"][0]["message"]["content"]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_file = RESULTS_DIR / f"{PROVIDER}_tests_raw_{ts}.txt"
    raw_file.write_text(content, encoding="utf-8")
    print(f"Raw-Antwort gespeichert → {raw_file}")

    test_blocks = [line for line in content.splitlines() if line.strip().startswith("===== FILE:")]
    total_tests = len(test_blocks)
    print(f"Anzahl generierter Testdateien: {total_tests}")

    print("Extrahiere und speichere Tests...")
    current_content = ""
    current_marker = None
    saved_count = 0

    for raw_line in content.splitlines(keepends=True):
        if "===== FILE:" in raw_line:
            if current_marker and current_content.strip():
                if save_generated_test(current_marker, current_content):
                    saved_count += 1

            start_idx = raw_line.find("===== FILE:") + len("===== FILE:")
            path_part = raw_line[start_idx:].strip()
            clean_path = path_part.split("=====", 1)[0].strip()

            current_marker = "===== FILE: " + clean_path
            current_content = ""
            print(f"Testblock → {clean_path}")
        else:
            current_content += raw_line

    if current_marker and current_content.strip():
        if save_generated_test(current_marker, current_content):
            saved_count += 1

    print(f"\nTestgenerierung abgeschlossen!")
    print(f"   Generiert (Marker gefunden): {total_tests}")
    print(f"   Erfolgreich gespeichert:      {saved_count}")
    if total_tests > saved_count:
        print(f"   ⚠️  {total_tests - saved_count} Test(s) übersprungen (Pfad-/Parse-Fehler)")
    print(f"   Tests liegen in:\n      {GENERATED_TESTS_DIR}\n")

# ----------------------------- CLI -----------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="LLM Test- & Fault-Analyse")
    parser.add_argument("--test-mode", action="store_true", help="Testgenerierung aktivieren")
    parser.add_argument("--clear-tests", action="store_true", help="Vorher alle alten Tests löschen (empfohlen!)")
    return parser.parse_args()

def main():
    args = parse_args()
    code = load_code()

    print(f"Provider: {PROVIDER.upper()} | Model: {MODEL}")
    print(f"Modus: {'🧪Testgenerierung' if args.test_mode else 'Fault Localization'}\n")

    if args.test_mode:
        run_test_generation(code, clear_first=args.clear_tests)
    else:
        run_fault_localization(code)

if __name__ == "__main__":
    main()