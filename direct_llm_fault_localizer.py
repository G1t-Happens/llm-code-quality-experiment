#!/usr/bin/env python3
import json
import os
import hashlib
import argparse
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Literal, Any, Optional

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
USER_PROMPT_TEST_FILE = BASE_DIR / "docs" / "experiment" / "llm_config" / "user_prompt_test.txt"
ENV_FILE = BASE_DIR / "docs" / "experiment" / "llm_config" / ".env"
RESULTS_DIR = BASE_DIR / "docs" / "experiment" / "results"
GENERATED_TESTS_DIR = BASE_DIR / "generated_tests"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)

dotenv.load_dotenv(ENV_FILE)

# ----------------------------- Reproduzierbarkeit Setup -----------------------------
code_content = CODE_FILE.read_text(encoding="utf-8")
CODE_MD5 = hashlib.md5(code_content.encode("utf-8")).hexdigest()

# ----------------------------- LLM Konfiguration aus .env -----------------------------
PROVIDER = os.getenv("PROVIDER", "grok").lower()
TEMPERATURE = os.getenv("TEMPERATURE")
if TEMPERATURE is not None:
    try:
        TEMPERATURE = float(TEMPERATURE)
        if TEMPERATURE < 0 or TEMPERATURE > 2:
            raise ValueError
    except ValueError:
        raise ValueError("TEMPERATURE muss eine Zahl zwischen 0.0 und 2.0 sein oder gar nicht gesetzt werden!")
else:
    TEMPERATURE = None

TOP_P = os.getenv("TOP_P")
if TOP_P is not None:
    try:
        TOP_P = float(TOP_P)
        if TOP_P < 0 or TOP_P > 1:
            raise ValueError
    except ValueError:
        raise ValueError("TOP_P muss eine Zahl zwischen 0.0 und 1.0 sein oder gar nicht gesetzt werden!")
else:
    TOP_P = None
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "32768"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "600"))


if PROVIDER == "grok":
    API_KEY = os.getenv("GROK_API_KEY")
    MODEL = os.getenv("GROK_MODEL", "grok-4-fast-non-reasoning")
    API_BASE = os.getenv("GROK_API_BASE", "https://api.x.ai/v1").rstrip("/")
elif PROVIDER == "openai":
    API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
    API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
else:
    raise ValueError(f"Ungültiger PROVIDER: {PROVIDER}. Erlaubt: 'grok' oder 'openai'")

if not API_KEY:
    raise ValueError(f"{PROVIDER.upper()}_API_KEY fehlt in der .env-Datei!")

run_hash = hashlib.sha1(
    f"{PROVIDER}|{MODEL}|{TEMPERATURE}|{TOP_P}|{MAX_TOKENS}|{CODE_MD5}".encode("utf-8")
).hexdigest()[:12]

short_model = MODEL.replace("/", "-").replace(":", "-").replace(" ", "_")
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
file_suffix = f"{ts}_{run_hash}"

# ----------------------------- Pydantic Models -----------------------------
SeverityLevel = Literal["critical", "high", "medium", "low"]

class SeededBug(BaseModel):
    filename: str = Field(..., description="Dateiname relativ zum Projektroot")
    start_line: int = Field(..., ge=1, description="Erste betroffene Zeile (1-basiert)")
    end_line: int = Field(..., ge=1, description="Letzte betroffene Zeile (inklusive)")
    severity: SeverityLevel = Field(..., description="Schweregrad des Fehlers")
    error_description: str = Field(..., min_length=10, description="Detaillierte Fehlerbeschreibung")

    model_config = {"extra": "forbid"}  # Hilft bei Validierung, aber Schema braucht explizit additionalProperties

class BugList(BaseModel):
    bugs: List[SeededBug] = Field(default_factory=list, description="Liste aller erkannter Fehler")

    model_config = {"extra": "forbid"}

# ----------------------------- Schema Utility für OpenAI Structured Outputs -----------------------------
def get_openai_compatible_schema(base_model: BaseModel) -> Dict[str, Any]:
    schema = base_model.model_json_schema()

    def enforce_strict(obj: Dict[str, Any]) -> Dict[str, Any]:
        if obj.get("type") == "object":
            # 1. additionalProperties: false
            obj["additionalProperties"] = False

            # 2. WICHTIG: required = alle keys aus properties!
            if "properties" in obj and obj.get("required") is None:
                obj["required"] = list(obj["properties"].keys())

            # Optional: strict explizit setzen
            obj["strict"] = True

        # Rekursion für nested objects, arrays, anyOf etc.
        for key, value in list(obj.items()):
            if isinstance(value, dict):
                obj[key] = enforce_strict(value)
            elif isinstance(value, list):
                obj[key] = [enforce_strict(item) if isinstance(item, dict) else item for item in value]

        return obj

    return enforce_strict(schema)

# ----------------------------- File Utilities -----------------------------
def load_file(file_path: Path) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")
    content = file_path.read_text(encoding="utf-8")
    return content.strip()

def load_code() -> str:
    code = CODE_FILE.read_text(encoding="utf-8")
    md5 = hashlib.md5(code.encode("utf-8")).hexdigest()
    print(f"Code geladen: {len(code):,} Zeichen | MD5: {md5}")
    return code

# ----------------------------- Test Generation Helpers -----------------------------
def clear_generated_tests() -> None:
    if GENERATED_TESTS_DIR.exists() and any(GENERATED_TESTS_DIR.iterdir()):
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
            raise ValueError(f"Kann Java-Package nicht erkennen: {marker_path}")

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
        print(f"PARSE-FEHLER bei Pfad '{path_str}': {e}")
        return False

    try:
        p = Path(path_str)
        com_idx = list(p.parts).index("com")
        package = ".".join(p.parts[com_idx:-1])
    except Exception:
        package = "com.llmquality.baseline"

    java_content = content.strip()
    if not java_content.lstrip().startswith("package "):
        java_content = f"package {package};\n\n{java_content}"

    test_path.write_text(java_content, encoding="utf-8")
    print(f"Test gespeichert → {test_path}")
    return True

def clean_java_content(raw_content: str, file_path: str = "") -> str:
    original = raw_content
    cleaned = raw_content.strip()

    code_block_patterns = [
        "```java", "```kotlin", "```python", "```javascript", "```js", "```ts",
        "```xml", "```json", "```yaml", "```yml", "```text", "```bash", "```sh", "```"
    ]
    for pattern in code_block_patterns:
        if cleaned.startswith(pattern):
            cleaned = cleaned[len(pattern):].lstrip("\n")
            break
    while cleaned.endswith("```"):
        cleaned = cleaned[:-3].rstrip("\n")

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
        "Hier ist der", "Hier sind die", "Hier ist eine", "Unten findest du",
        "Der folgende Code", "Der generierte Test", "Die Testklasse",
        "Explanation:", "Note:", "Important:", "Warning:", "Hinweis:",
        "```", "<!--", "#", "//", "/*", "*"
    ]

    lines = cleaned.splitlines()
    filtered = []
    for line in lines:
        stripped = line.strip()
        if not stripped and not filtered:
            continue
        if any(stripped.startswith(p) for p in garbage_prefixes):
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
            result = result[:start] + result[end + 3:]
        result = result.strip()

    if original.strip() != result and result:
        fname = Path(file_path).name if file_path else "unknown"
        print(f"  → Bereinigt (Garbage/Markdown entfernt): {fname}")

    return result + ("\n" if result else "")

# ----------------------------- LLM Clients -----------------------------
class GrokClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        })

    def chat(self, messages: List[Dict], use_structured: bool = False, schema: Optional[BaseModel] = None) -> Dict:
        payload = {
            "model": MODEL,
            "messages": messages,
            "max_tokens": MAX_TOKENS,
        }

        if TEMPERATURE is not None:
            payload["temperature"] = TEMPERATURE
        if TOP_P is not None:
            payload["top_p"] = TOP_P
        if use_structured and schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "bug_list",
                    "strict": True,
                    "schema": get_openai_compatible_schema(schema)
                }
            }

        resp = self.session.post(
            f"{API_BASE}/chat/completions",
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()

    def close(self):
        self.session.close()


class OpenAIResponsesClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=API_KEY,
            base_url=API_BASE,
            timeout=REQUEST_TIMEOUT
        )

    def create(self, input: str | list, instructions: Optional[str] = None, structured_schema: Optional[BaseModel] = None, **kwargs) -> Any:
        params: Dict[str, Any] = {
            "model": MODEL,
            "input": input,
            "max_output_tokens": MAX_TOKENS,
            **kwargs
        }
        if instructions:
            params["instructions"] = instructions

        if TEMPERATURE is not None:
            params["temperature"] = TEMPERATURE

        if TOP_P is not None:
            params["top_p"] = TOP_P

        if structured_schema:
            compatible_schema = get_openai_compatible_schema(structured_schema)
            params["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "bug_list",
                    "strict": True,
                    "schema": compatible_schema
                }
            }

        return self.client.responses.create(**params)

    def close(self):
        self.client.close()


# ----------------------------- Core Logic: Fault Localization -----------------------------
def run_fault_localization(code: str):
    system_prompt = load_file(SYSTEM_PROMPT_FAULT_FILE)
    user_prompt = load_file(USER_PROMPT_FAULT_FILE).format(code=code)

    instructions = system_prompt
    user_input = user_prompt

    temp_str = f"temp={TEMPERATURE:.1f}" if TEMPERATURE is not None else "temp=<auto>"
    top_p_str = f"top_p={TOP_P:.2f}" if TOP_P is not None else "top_p=<auto>"
    print(f"Starte Fault Localization → {PROVIDER.upper():6} | {MODEL:30} | {temp_str} | {top_p_str} | max_tokens={MAX_TOKENS}")

    raw_response = None
    content = ""

    if PROVIDER == "grok":
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        client = GrokClient()
        try:
            raw_response = client.chat(messages, use_structured=True, schema=BugList)
            content = raw_response["choices"][0]["message"]["content"]
        finally:
            client.close()

    else:  # OpenAI Responses API
        client = OpenAIResponsesClient()
        try:
            response = client.create(
                instructions=instructions,
                input=user_input,
                structured_schema=BugList
            )
            raw_response = response.model_dump()
            content = response.output_text
        finally:
            client.close()

        # --- ULTRA-ROBUSTER PARSER 2025 – funktioniert mit Grok, Claude, GPT-4o, DeepSeek, Llama ---
        # --- 100% ROBUSTER + PYTHON 3.8–3.13 KOMPATIBLER PARSER (2025 Gold Standard) ---
    def parse_bug_output(text: str) -> BugList:
        text = text.strip()
        findings = []

        # 1. Falls es doch ein normales JSON-Array kommt
        if text.startswith("["):
            try:
                data = json.loads(text)
                if isinstance(data, list):
                    return BugList.model_validate({"bugs": data})
                return BugList.model_validate(data)
            except json.JSONDecodeError:
                pass

        # 2. JSON Lines: einfach alles finden, was wie ein { ... } aussieht
        # Kein rekursives Regex → funktioniert überall
        import re
        potential_jsons = re.findall(r'\{[^{}]*\}', text)  # erst grob alle einfachen Objekte
        # Fallback: auch verschachtelte mit geschachtelten Klammern (sicher und schnell)
        matches = re.finditer(r'\{(?:\{[^{}]*\}|[^{}])*\}', text)

        for match in matches:
            obj_str = match.group(0)
            try:
                # Trailing comma reparieren
                cleaned = re.sub(r',\s*}', '}', obj_str)
                cleaned = re.sub(r',\s*]', ']', cleaned)
                data = json.loads(cleaned)

                bug = {
                    "filename": data.get("filename") or data.get("file", "unknown.java"),
                    "start_line": int(data["start_line"]),
                    "end_line": int(data.get("end_line", data["start_line"])),
                    "severity": str(data.get("severity", "medium")).lower(),
                    "error_description": data.get("error_description") or data.get("description") or "No description"
                }
                findings.append(bug)
            except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
                continue  # kaputte Objekte ignorieren

        # 3. Ultimativer Fallback: alles zwischen erstem { und letztem }
        if not findings and "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            try:
                data = json.loads(text[start:end])
                if isinstance(data, dict):
                    findings = [data]
                elif isinstance(data, list):
                    findings = data
            except:
                pass

        if not findings:
            raise ValueError("Kein einziges gültiges JSON-Objekt gefunden – LLM hat komplett versagt.")

        return BugList.model_validate({"bugs": findings})

    try:
        bug_list = parse_bug_output(content)
        print(f"Erfolgreich geparst → {len(bug_list.bugs)} Bug(s) erkannt!")
    except Exception as e:
        print(f"JSON-Parsing fehlgeschlagen: {e}")
        print("Erste 3000 Zeichen der Ausgabe:")
        print(content[:3000])
        raise

    bugs_data = [bug.model_dump() for bug in bug_list.bugs]

    prefix = f"{short_model}_fault"
    raw_file = RESULTS_DIR / f"{prefix}_raw_{file_suffix}.json"
    bugs_file = RESULTS_DIR / f"{prefix}_bugs_{file_suffix}.json"
    raw_file.write_text(json.dumps(raw_response, indent=2, ensure_ascii=False), encoding="utf-8")
    bugs_file.write_text(json.dumps(bugs_data, indent=2, ensure_ascii=False), encoding="utf-8")

    metadata = {
        "provider": PROVIDER,
        "model": MODEL,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": MAX_TOKENS,
        "code_md5": CODE_MD5,
        "code_length": len(code_content),
        "timestamp": datetime.now().isoformat(),
        "run_hash": run_hash,
        "system_prompt_md5": hashlib.md5(system_prompt.encode("utf-8")).hexdigest(),
        "user_prompt_md5": hashlib.md5(user_prompt.encode("utf-8")).hexdigest(),
        "detected_bugs": len(bugs_data)
    }
    meta_file = RESULTS_DIR / f"{prefix}_meta_{file_suffix}.json"
    meta_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Fault Localization abgeschlossen!")
    print(f"   → {len(bugs_data)} Bug(s) gefunden")
    print(f"   → Raw:  {raw_file}")
    print(f"   → Bugs: {bugs_file}")
    print(f"   → Meta: {meta_file}\n")

# ----------------------------- Core Logic: Test Generation -----------------------------
def run_test_generation(code: str, clear_first: bool):
    if clear_first:
        clear_generated_tests()

    system_prompt = load_file(SYSTEM_PROMPT_TEST_FILE)
    user_prompt = load_file(USER_PROMPT_TEST_FILE).format(code=code) + \
                  "\n\nGeneriere vollständige JUnit 5 Testklassen mit korrekten Dateimarkern (===== FILE: ... =====)."

    instructions = system_prompt
    user_input = user_prompt

    temp_str = f"temp={TEMPERATURE:.1f}" if TEMPERATURE is not None else "temp=<auto>"
    top_p_str = f"top_p={TOP_P:.2f}" if TOP_P is not None else "top_p=<auto>"
    print(f"Starte Testgenerierung → {PROVIDER.upper():6} | {MODEL:30} | {temp_str} | {top_p_str} | max_tokens={MAX_TOKENS}")

    raw_response = None
    content = ""

    if PROVIDER == "grok":
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        client = GrokClient()
        try:
            raw_response = client.chat(messages)
            content = raw_response["choices"][0]["message"]["content"]
        finally:
            client.close()

    else:
        client = OpenAIResponsesClient()
        try:
            response = client.create(
                instructions=instructions,
                input=user_input
            )
            raw_response = response.model_dump()
            content = response.output_text
        finally:
            client.close()

    full_raw_file = RESULTS_DIR / f"{short_model}_tests_raw_{file_suffix}.json"
    txt_raw_file = RESULTS_DIR / f"{short_model}_tests_raw_{file_suffix}.txt"
    full_raw_file.write_text(json.dumps(raw_response, indent=2, ensure_ascii=False), encoding="utf-8")
    txt_raw_file.write_text(content, encoding="utf-8")

    print(f"Rohantwort gespeichert → {txt_raw_file}")

    # --- Parser für ===== FILE: Marker ---
    parsed_tests = []
    current_marker: Optional[str] = None
    current_content = ""

    for raw_line in content.splitlines(keepends=True):
        if raw_line.strip().startswith("===== FILE:"):
            if current_marker and current_content.strip():
                path_str = current_marker[len("===== FILE:"):].strip().split("=====", 1)[0].strip()
                cleaned = clean_java_content(current_content, path_str)
                if cleaned.strip():
                    save_generated_test(current_marker, cleaned)
                    parsed_tests.append({"file_path": path_str, "content": cleaned})
                else:
                    print(f"Leer nach Bereinigung → übersprungen: {path_str}")
            current_marker = raw_line.strip()
            current_content = ""
        else:
            current_content += raw_line

    if current_marker and current_content.strip():
        path_str = current_marker[len("===== FILE:"):].strip().split("=====", 1)[0].strip()
        cleaned = clean_java_content(current_content, path_str)
        if cleaned.strip():
            save_generated_test(current_marker, cleaned)
            parsed_tests.append({"file_path": path_str, "content": cleaned})

    parsed_file = RESULTS_DIR / f"{short_model}_tests_parsed_{file_suffix}.json"
    parsed_file.write_text(json.dumps(parsed_tests, indent=2, ensure_ascii=False), encoding="utf-8")

    metadata = {
        "provider": PROVIDER,
        "model": MODEL,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": MAX_TOKENS,
        "code_md5": CODE_MD5,
        "code_length": len(code_content),
        "timestamp": datetime.now().isoformat(),
        "run_hash": run_hash,
        "system_prompt_md5": hashlib.md5(system_prompt.encode("utf-8")).hexdigest(),
        "user_prompt_md5": hashlib.md5(user_prompt.encode("utf-8")).hexdigest(),
        "generated_tests": len(parsed_tests)
    }
    meta_file = RESULTS_DIR / f"{short_model}_tests_meta_{file_suffix}.json"
    meta_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Testgenerierung abgeschlossen!")
    print(f"   → {len(parsed_tests)} Testdatei(en) generiert")
    print(f"   → Tests in: {GENERATED_TESTS_DIR}")
    print(f"   → Metadaten: {meta_file}\n")

# ----------------------------- CLI & Main -----------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="LLM-gestützte Fault Localization & Testgenerierung")
    parser.add_argument("--test-mode", action="store_true", help="Testgenerierung statt Fault Localization")
    parser.add_argument("--clear-tests", action="store_true", help="Alten Testordner vor Generierung löschen")
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