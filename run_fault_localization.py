#!/usr/bin/env python3

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, List

import dotenv
import requests
from openai import APIError, OpenAI, RateLimitError as OpenAIRateLimitError
from openai import Timeout as OpenAITimeout
from pydantic import BaseModel, Field

# ----------------------------- Config -----------------------------
BASE_DIR = Path(__file__).parent.resolve()
CODE_FILE = BASE_DIR / "docs" / "experiment" / "code_under_test" / "extracted_code.txt"
SYSTEM_PROMPT_FILE = BASE_DIR / "docs" / "experiment" / "llm_config" / "system_prompt.txt"
USER_PROMPT_FILE = BASE_DIR / "docs" / "experiment" / "llm_config" / "user_prompt.txt"
ENV_FILE = BASE_DIR / "docs" / "experiment" / "llm_config" / ".env"
RESULTS_DIR = BASE_DIR / "docs" / "experiment" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
dotenv.load_dotenv(ENV_FILE)

# ----------------------------- Env Vars -----------------------------
PROVIDER = os.getenv("PROVIDER", "grok").lower()
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "32768"))
O1_MAX_COMPLETION_TOKENS = int(os.getenv("O1_MAX_COMPLETION_TOKENS", "32768"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "600"))
TOP_P = float(os.getenv("TOP_P", "0.90"))
DEBUG = os.getenv("DEBUG", "0") == "1"  # Currently unused, but preserved

# Provider-specific vars
if PROVIDER == "grok":
    API_KEY = os.getenv("GROK_API_KEY")
    MODEL = os.getenv("GROK_MODEL", "grok-4-fast-non-reasoning")
    API_BASE = os.getenv("GROK_API_BASE", "https://api.x.ai/v1").rstrip("/")
elif PROVIDER == "openai":
    API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
    API_BASE = os.getenv("OPENAI_API_BASE") or None
else:
    raise ValueError(f"Ungültiger PROVIDER: {PROVIDER}. Muss 'grok' oder 'openai' sein.")

if not API_KEY:
    raise ValueError(f"{PROVIDER.upper()}_API_KEY fehlt in deiner .env!")

# ----------------------------- Pydantic Schema -----------------------------
class SeededBug(BaseModel):
    filename: str
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    severity: str = Field(..., pattern="^(critical|high|medium|low)$")
    error_description: str

class BugList(BaseModel):
    bugs: List[SeededBug]

# ----------------------------- Prompts & Code -----------------------------
def load_text_file(file_path: Path) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return file_path.read_text(encoding="utf-8").strip()

SYSTEM_PROMPT = load_text_file(SYSTEM_PROMPT_FILE)
USER_PROMPT_TEMPLATE = load_text_file(USER_PROMPT_FILE)

def load_code() -> str:
    code = load_text_file(CODE_FILE)
    md5 = hashlib.md5(code.encode()).hexdigest()
    print(f"Code loaded: {len(code):,} characters | MD5: {md5}")
    return code

# ----------------------------- Grok Client -----------------------------
class GrokClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        })

    def chat_completions_parse(self, **kwargs: Any) -> Any:
        payload = {
            **kwargs,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "bug_list",
                    "strict": True,
                    "schema": kwargs["response_format"].model_json_schema()
                }
            }
        }
        response = self.session.post(
            f"{API_BASE}/chat/completions",
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        raw_content = data["choices"][0]["message"]["content"]
        parsed_data = json.loads(raw_content)
        parsed_obj = kwargs["response_format"].model_validate(parsed_data)

        # Fake OpenAI-compatible object
        class Message:
            content = raw_content
            parsed = parsed_obj

        class Choice:
            message = Message()

        class Completion:
            choices = [Choice()]

            def model_dump_json(self, indent: int = 2) -> str:
                return json.dumps(data, indent=indent, ensure_ascii=False)

        return Completion()

    def close(self) -> None:
        self.session.close()

# ----------------------------- LLM Calls -----------------------------
def call_grok(client: GrokClient, model: str, code: str) -> Any:
    user_msg = USER_PROMPT_TEMPLATE.format(code=code)
    print(f"Calling Grok → Model: {model}")
    call_kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ],
        "response_format": BugList,
        "max_completion_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
    }
    start_time = time.time()
    for attempt in range(1, 6):
        try:
            print("Calling Grok with native Structured Outputs...")
            completion = client.chat_completions_parse(**call_kwargs)
            duration = time.time() - start_time
            print(f"→ Response received in {duration:.1f}s!")
            return completion
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt < 5:
                time.sleep(20)
            else:
                raise
    raise RuntimeError("Max retries exceeded – API nicht erreichbar")

def call_openai(client: OpenAI, model: str, code: str) -> Any:
    user_msg = USER_PROMPT_TEMPLATE.format(code=code)
    print(f"Calling model '{model}' with Structured Outputs...")
    # Detect reasoning models (o1, o3, gpt-5, gpt-4.5 etc.)
    is_reasoning_model = any(x in model.lower() for x in ["o1", "o3", "gpt-5", "gpt-4.5"])
    call_kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ],
        "response_format": BugList,
        "max_completion_tokens": O1_MAX_COMPLETION_TOKENS if is_reasoning_model else MAX_TOKENS,
        "top_p": TOP_P,
    }
    # Only non-reasoning models allow temperature
    if not is_reasoning_model:
        call_kwargs["temperature"] = TEMPERATURE
        print(f"→ Standard-Modell → temperature={TEMPERATURE}, max_completion_tokens={MAX_TOKENS}")
    else:
        print(f"→ Reasoning-Modell ({model}) → temperature wird automatisch auf 1.0 gesetzt, max_completion_tokens={O1_MAX_COMPLETION_TOKENS}")
    start_time = time.time()
    for attempt in range(1, 5):
        try:
            completion = client.chat.completions.parse(**call_kwargs)
            duration = time.time() - start_time
            print(f"Response received in {duration:.1f}s")
            return completion
        except (OpenAITimeout, OpenAIRateLimitError) as e:
            print(f"Attempt {attempt}: {type(e).__name__} – warte 20s...")
            time.sleep(20)
        except APIError as e:
            error_message = str(e).lower()
            if "temperature" in error_message or "unsupported value" in error_message:
                print("→ Temperature nicht erlaubt → entferne Parameter und retry")
                call_kwargs.pop("temperature", None)
                continue
            if "max_completion_tokens" in error_message:
                print("→ max_completion_tokens zu hoch → reduziere auf 16384 und retry")
                call_kwargs["max_completion_tokens"] = 16384
                continue
            print(f"OpenAI API Fehler: {e}")
            raise
        except Exception as e:
            print(f"Unerwarteter Fehler: {e}")
            raise
    raise RuntimeError("Max retries exceeded – API nicht erreichbar")

# ----------------------------- Run Analysis -----------------------------
def run_analysis(code: str) -> Any:
    if PROVIDER == "grok":
        client = GrokClient()
        try:
            return call_grok(client, MODEL, code)
        finally:
            client.close()
    elif PROVIDER == "openai":
        client = OpenAI(
            api_key=API_KEY,
            base_url=API_BASE,
            timeout=REQUEST_TIMEOUT,
        )
        return call_openai(client, MODEL, code)
    else:
        raise ValueError(f"Unbekannter PROVIDER: {PROVIDER}")

# ----------------------------- Save Results -----------------------------
def save_results(completion: Any, bugs: List[dict[str, Any]]) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = PROVIDER
    raw_file = RESULTS_DIR / f"{prefix}_raw_{ts}.json"
    bugs_file = RESULTS_DIR / f"{prefix}_faults_{ts}.json"
    raw_file.write_text(completion.model_dump_json(indent=2), encoding="utf-8")
    bugs_file.write_text(json.dumps(bugs, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSUCCESS! {PROVIDER.capitalize()} found {len(bugs)} seeded bug(s)!")
    print(f" Raw response → {raw_file}")
    print(f" Detected bugs → {bugs_file}\n")

# ----------------------------- Main -----------------------------
def main() -> None:
    code = load_code()
    print(f"Using provider: {PROVIDER.upper()} | Model: {MODEL}\n")
    completion = run_analysis(code)
    parsed: BugList = completion.choices[0].message.parsed
    bugs = [bug.model_dump() for bug in parsed.bugs]
    save_results(completion, bugs)

if __name__ == "__main__":
    main()