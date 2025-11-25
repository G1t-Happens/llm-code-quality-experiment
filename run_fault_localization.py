#!/usr/bin/env python3
import json
import os
import hashlib
import argparse
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Literal

import dotenv
from pydantic import BaseModel, Field
import requests
from openai import OpenAI

# ----------------------------- Constants & Paths -----------------------------
BASE_DIR = Path(__file__).parent.resolve()

CODE_FILE = BASE_DIR / "docs" / "experiment" / "code_under_test" / "extracted_code.txt"
SYSTEM_PROMPT_FAULT_FILE = BASE_DIR / "docs" / "experiment" / "llm_config" / "system_prompt_fault.txt"
SYSTEM_PROMPT_TEST_FILE = BASE_DIR / "docs" / "experiment" / "llm_config" / "system_prompt_test.txt"
USER_PROMPT_FAULT_FILE = BASE_DIR / "docs" / "experiment" / "llm_config" / "user_prompt_fault.txt"
USER_PROMPT_TEST_FILE  = BASE_DIR / "docs" / "experiment" / "llm_config" / "user_prompt_test.txt"
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
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "600"))
TOP_P = float(os.getenv("TOP_P", "0.90"))

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

# ----------------------------- Pydantic Models -----------------------------
SeverityLevel = Literal["critical", "high", "medium", "low"]

class SeededBug(BaseModel):
    filename: str = Field(..., description="Filename relative to the project root")
    start_line: int = Field(..., ge=1, description="First affected line (1-based)")
    end_line: int = Field(..., ge=1, description="Last affected line (1-based)")
    severity: SeverityLevel = Field(..., description="Severity level of the bug")
    error_description: str = Field(..., min_length=10, description="Detailed description of the error")

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

# ----------------------------- Test Generation Helpers -----------------------------
def clear_generated_tests():
    if GENERATED_TESTS_DIR.exists():
        print(f"Lösche alten Test-Ordner: {GENERATED_TESTS_DIR}")
        shutil.rmtree(GENERATED_TESTS_DIR)
    GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)

def resolve_test_path(marker_path: str) -> Path:
    path = Path(marker_path.strip())

    try:
        com_index = list(path.parts).index("com")
        relative_parts = path.parts[com_index:]
    except ValueError:
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

def save_generated_test(file_marker: str, content: str) -> bool:
    if not file_marker.strip().startswith("===== FILE:"):
        return False

    path_str = file_marker[len("===== FILE:"):].strip().split("=====", 1)[0].strip()
    if not path_str:
        return False

    try:
        test_path = resolve_test_path(path_str)
    except Exception as e:
        print(f"PARSE-FEHLER bei: {path_str} → {e}")
        return False

    try:
        p = Path(path_str)
        com_idx = list(p.parts).index("com")
        package = ".".join(p.parts[com_idx:-1])
    except Exception:
        package = "com.llmquality.baseline"

    java_content = content.strip()

    # Nur einfügen, wenn noch KEINE package-Zeile existiert (robust gegen LLM-Doppelungen)
    if not java_content.lstrip().startswith("package "):
        java_content = f"package {package};\n\n{java_content}"

    test_path.write_text(java_content, encoding="utf-8")
    print(f"Test gespeichert → {test_path}")
    return True

# ----------------------------- Markdown & Garbage Cleaner -----------------------------
def clean_java_content(raw_content: str, file_path: str = "") -> str:
    original = raw_content
    cleaned = raw_content.strip()

    code_block_patterns = [
        "```java", "```kotlin", "```python", "```javascript", "```js", "```ts",
        "```xml", "```json", "```yaml", "```yml", "```text", "```bash", "```sh", "```"
    ]
    for pattern in code_block_patterns:
        if cleaned.startswith(pattern):
            rest = cleaned[len(pattern):].lstrip("\n")
            cleaned = rest
            break

    while cleaned.endswith("```"):
        cleaned = cleaned[:-3].rstrip()

    garbage_prefixes = [
        "Here is the", "Here are the", "Here's the", "Here is a", "Here are some",
        "This is the", "These are the", "Below is the", "Following is the",
        "The following", "Provided below", "Here you go", "Sure, here is",
        "As requested", "Here is your", "I have generated", "Generated test",
        "The generated test", "The test class", "The unit test", "The JUnit test",
        "Unit test class", "JUnit test class", "Test class for", "Tests for",
        "Here is the complete", "Here is the full", "Here is the updated",
        "I've created the", "I've written the", "I have written the",
        "Please find the", "Attached is the", "Enclosed is the",
        "The code is as follows", "The implementation is",
        # Deutsch
        "Hier ist der", "Hier sind die", "Hier ist eine", "Unten findest du",
        "Der folgende Code", "Der generierte Test", "Die Testklasse",
        # Sonstiges
        "Explanation:", "Note:", "Important:", "Warning:", "Hinweis:",
        "```", "<!--", "#", "//", "/*", "*"
    ]

    lines = cleaned.splitlines()
    filtered = []
    for line in lines:
        stripped = line.strip()

        if not stripped and not filtered:
            continue

        if any(stripped.startswith(prefix) for prefix in garbage_prefixes):
            continue

        if stripped.startswith((">", "|", "Diff", "diff --git", "---", "+++")):
            continue
        if stripped.isdigit() and len(stripped) <= 4:
            continue
        if stripped.startswith(("Example:", "Beispiel:", "Output:", "Result:")):
            continue

        filtered.append(line)

    result = "\n".join(filtered).strip()

    if "```" in result:
        start = result.find("```")
        end = result.rfind("```")
        if start != -1 and end != -1 and start < end:
            result = result[:start] + result[end + 3 :]
        result = result.strip()

    if original != result + "\n":
        fname = Path(file_path).name if file_path else "unknown"
        print(f"  → Bereinigt (Markdown/Garbage entfernt): {fname}")

    return result + ("\n" if result else "")

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
    system_prompt = load_file(SYSTEM_PROMPT_FAULT_FILE)
    user_prompt   = load_file(USER_PROMPT_FAULT_FILE).format(code=code)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    print(f"Starte Fault Localization → {PROVIDER.upper():6} | {MODEL:30} | "
          f"temp={TEMPERATURE:.1f} | top_p={TOP_P:.2f} | max_tokens={MAX_TOKENS}")
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

    raw_content = data["choices"][0]["message"]["content"].strip()

    def parse_grok_output(text: str) -> BugList:
        raw = text.strip()
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1 or end == 0:
            raise ValueError("Kein JSON-Array gefunden!")

        candidate = raw[start:end]

        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return BugList.model_validate({"bugs": parsed})
            elif isinstance(parsed, dict) and "bugs" in parsed:
                return BugList.model_validate(parsed)
        except json.JSONDecodeError:
            pass

        objects = re.findall(r'\{[^{}]*"filename"[^{}]*"error_description"[^{}]*\}', candidate, re.DOTALL)
        if not objects:
            objects = re.findall(r'\{[^{}]*"filename"[^{}]*\}', candidate, re.DOTALL)
        if objects:
            cleaned = "[" + ",".join(objects) + "]"
            parsed_list = json.loads(cleaned)
            return BugList.model_validate({"bugs": parsed_list})

        raise ValueError("Konnte Grok-JSON nicht reparieren!")

    try:
        parsed = parse_grok_output(raw_content)
        print(f"JSON erfolgreich geparst → {len(parsed.bugs)} Bug(s) erkannt!")
    except Exception as e:
        print("Parser fehlgeschlagen!")
        print(raw_content[:5000])
        raise

    bugs = [bug.model_dump() for bug in parsed.bugs]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_model = "-".join(MODEL.split("-")[:2])
    prefix = f"{short_model}_fault"

    raw_file = RESULTS_DIR / f"{prefix}_raw_{ts}.json"
    bugs_file = RESULTS_DIR / f"{prefix}_bugs_{ts}.json"

    raw_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    bugs_file.write_text(json.dumps(bugs, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nFault Localization abgeschlossen! {len(bugs)} Bug(s) gefunden.")
    print(f"   Raw  → {raw_file}")
    print(f"   Bugs → {bugs_file}\n")

# ----------------------------- Test Generation -----------------------------
def run_test_generation(code: str, clear_first: bool):
    if clear_first:
        clear_generated_tests()

    system_prompt = load_file(SYSTEM_PROMPT_TEST_FILE)
    user_prompt   = load_file(USER_PROMPT_TEST_FILE).format(code=code)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt + "\n\nGeneriere vollständige JUnit 5 Testklassen mit korrekten Dateimarkern."}
    ]

    print(f"Starte Testgenerierung → {PROVIDER.upper():6} | {MODEL:30} | "
          f"temp={TEMPERATURE:.1f} | top_p={TOP_P:.2f} | max_tokens={MAX_TOKENS}")

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
            temperature=TEMPERATURE,
            top_p=TOP_P,
            max_completion_tokens=MAX_TOKENS,
        )
        data = completion.model_dump()

    content = data["choices"][0]["message"]["content"]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_model = "-".join(MODEL.split("-")[:2])

    full_raw_file = RESULTS_DIR / f"{short_model}_tests_raw_{ts}.json"
    full_raw_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    txt_raw_file = RESULTS_DIR / f"{short_model}_tests_raw_{ts}.txt"
    txt_raw_file.write_text(content, encoding="utf-8")

    print(f"Full API-Response  → {full_raw_file}")
    print(f"Roh-Text (Debug)   → {txt_raw_file}")

    # ------------------ ROBUSTER PARSER (kein doppeltes Append!) ------------------
    parsed_tests = []
    current_marker = None
    current_content = ""

    for raw_line in content.splitlines(keepends=True):
        if raw_line.strip().startswith("===== FILE:"):
            if current_marker and current_content.strip():
                path_str = current_marker[len("===== FILE:"):].strip().split("=====", 1)[0].strip()
                cleaned_content = clean_java_content(current_content, path_str)

                if cleaned_content.strip():
                    save_generated_test(current_marker, cleaned_content)
                    parsed_tests.append({
                        "file_path": path_str,
                        "content": cleaned_content
                    })
                else:
                    print(f"  → LEERER TEST nach Bereinigung → übersprungen: {path_str}")

            current_marker = raw_line.strip()
            current_content = ""
        else:
            current_content += raw_line

    # Letzte Datei verarbeiten
    if current_marker and current_content.strip():
        path_str = current_marker[len("===== FILE:"):].strip().split("=====", 1)[0].strip()
        cleaned_content = clean_java_content(current_content, path_str)

        if cleaned_content.strip():
            save_generated_test(current_marker, cleaned_content)
            parsed_tests.append({
                "file_path": path_str,
                "content": cleaned_content
            })
        else:
            print(f"  → LEERER TEST nach Bereinigung → übersprungen: {path_str}")

    # Geparste JSON-Datei speichern
    parsed_file = RESULTS_DIR / f"{short_model}_tests_parsed_{ts}.json"
    parsed_file.write_text(json.dumps(parsed_tests, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Geparste Tests     → {parsed_file} ({len(parsed_tests)} Dateien)")
    print(f"\nTestgenerierung abgeschlossen!")
    print(f"   Generiert: {len(parsed_tests)} Testdatei(en)")
    print(f"   Tests liegen in:\n      {GENERATED_TESTS_DIR}\n")

# ----------------------------- CLI -----------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="LLM Test- & Fault-Analyse")
    parser.add_argument("--test-mode", action="store_true", help="Testgenerierung aktivieren")
    parser.add_argument("--clear-tests", action="store_true", help="Vorher alle alten Tests löschen")
    return parser.parse_args()

def main():
    args = parse_args()
    code = load_code()

    print(f"Provider: {PROVIDER.upper()} | Model: {MODEL}")
    print(f"Modus: {'Testgenerierung' if args.test_mode else 'Fault Localization'}\n")

    if args.test_mode:
        run_test_generation(code, clear_first=args.clear_tests)
    else:
        run_fault_localization(code)

if __name__ == "__main__":
    main()