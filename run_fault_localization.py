#!/usr/bin/env python3
import json
import time
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Any

import dotenv
from openai import OpenAI, APIError, Timeout, RateLimitError
from pydantic import BaseModel, Field

# ----------------------------- Config -----------------------------
BASE_DIR = Path(__file__).parent.resolve()

CODE_FILE   = BASE_DIR / "docs" / "experiment" / "code_under_test" / "extracted_code.txt"
SYSTEM_PROMPT_FILE = BASE_DIR / "docs" / "experiment" / "llm_config" / "system_prompt.txt"
USER_PROMPT_FILE   = BASE_DIR / "docs" / "experiment" / "llm_config" / "user_prompt.txt"
ENV_FILE    = BASE_DIR / "docs" / "experiment" / "llm_config" / ".env"
RESULTS_DIR = BASE_DIR / "docs" / "experiment" / "results"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
dotenv.load_dotenv(ENV_FILE)


# ----------------------------- Umgebungsvariablen mit sinnvollen Defaults -----------------------------
OPENAI_MODEL            = os.getenv("OPENAI_MODEL", "gpt-4o-2024-11-20")
OPENAI_API_KEY          = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE         = os.getenv("OPENAI_API_BASE") or None

TEMPERATURE             = float(os.getenv("TEMPERATURE", "0.0"))
REQUEST_TIMEOUT         = int(os.getenv("REQUEST_TIMEOUT", "600"))          # Sekunden

# Maximale Output-Tokens (wird später ggf. überschrieben je nach Modell)
DEFAULT_MAX_TOKENS      = int(os.getenv("MAX_TOKENS", "16384"))             # safe für gpt-4o
O1_MAX_COMPLETION_TOKENS = int(os.getenv("O1_MAX_COMPLETION_TOKENS", "32768"))  # o1/o3 erlauben mehr

DEBUG                   = os.getenv("DEBUG", "0") == "1"


# ----------------------------- Pydantic Schema -----------------------------
class SeededBug(BaseModel):
    filename: str = Field(..., description="Java filename (e.g. MyClass.java)")
    start_line: int = Field(..., ge=1, description="Start line of the buggy code")
    end_line: int = Field(..., ge=1, description="End line of the buggy code")
    severity: str = Field(..., pattern="^(critical|high|medium|low)$")
    error_description: str = Field(..., description="Precise, technical bug description")

class BugList(BaseModel):
    bugs: List[SeededBug]


# ----------------------------- Prompts -----------------------------
def load_prompt(file_path: Path) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")
    return file_path.read_text(encoding="utf-8").strip()

SYSTEM_PROMPT = load_prompt(SYSTEM_PROMPT_FILE)
USER_PROMPT_TEMPLATE = load_prompt(USER_PROMPT_FILE)


# ----------------------------- Code Loader -----------------------------
def load_code() -> str:
    if not CODE_FILE.exists():
        raise FileNotFoundError(f"Code file not found: {CODE_FILE}")
    code = CODE_FILE.read_text(encoding="utf-8")
    md5 = hashlib.md5(code.encode()).hexdigest()
    print(f"Code loaded: {len(code):,} characters | MD5: {md5}")
    return code


# ----------------------------- LLM Call (dynamisch o1 vs. normal) -----------------------------
def call_llm(client: OpenAI, model: str, code: str):
    user_msg = USER_PROMPT_TEMPLATE.format(code=code)

    print(f"Calling model '{model}' with Structured Outputs...")
    if DEBUG:
        print(f"Temperature: {TEMPERATURE} | Timeout: {REQUEST_TIMEOUT}s")

    start_time = time.time()

    # Dynamische Parameter je nach Modellfamilie
    call_kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg}
        ],
        "temperature": TEMPERATURE,
        "timeout": REQUEST_TIMEOUT,
        "response_format": BugList,
    }

    # WICHTIG: o1- und o3-Modelle verwenden NICHT max_tokens, sondern max_completion_tokens
    is_reasoning_model = "o1" in model.lower() or "o3" in model.lower()
    if is_reasoning_model:
        call_kwargs["max_completion_tokens"] = O1_MAX_COMPLETION_TOKENS
        print(f"→ Reasoning-Modell erkannt → nutze max_completion_tokens = {O1_MAX_COMPLETION_TOKENS}")
    else:
        max_tokens = DEFAULT_MAX_TOKENS
        if "long-output" in model.lower():
            max_tokens = 65536
        call_kwargs["max_tokens"] = max_tokens
        print(f"→ Standard-Modell → nutze max_tokens = {max_tokens}")

    for attempt in range(1, 4):
        try:
            completion = client.chat.completions.parse(**call_kwargs)
            duration = time.time() - start_time
            print(f"Response received in {duration:.1f}s")
            return completion

        except (Timeout, RateLimitError) as e:
            print(f"Attempt {attempt}: {type(e).__name__} – retrying in 10s...")
            time.sleep(10)
        except APIError as e:
            print(f"OpenAI API Error: {e}")
            if DEBUG:
                print(f"Full error: {e!r}")
            raise
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise

    raise RuntimeError("Max retries exceeded – API nicht erreichbar")


# ----------------------------- Save Results -----------------------------
def save_results(completion, bugs: List[dict]):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_file = RESULTS_DIR / f"raw_response_{ts}.json"
    json_file = RESULTS_DIR / f"faults_detected_{ts}.json"

    raw_file.write_text(completion.model_dump_json(indent=2), encoding="utf-8")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(bugs, f, indent=2, ensure_ascii=False)

    print(f"\nSUCCESS! Found {len(bugs)} seeded bug(s)!")
    print(f"   Raw response  → {raw_file}")
    print(f"   Detected bugs → {json_file}\n")


# ----------------------------- Main -----------------------------
def main():
    code = load_code()

    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found in .env file!")

    client = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE,
        timeout=REQUEST_TIMEOUT,
    )

    print(f"Using model: {OPENAI_MODEL}\n")

    completion = call_llm(client, OPENAI_MODEL, code)

    parsed: BugList = completion.choices[0].message.parsed
    bug_list = [bug.model_dump() for bug in parsed.bugs]

    save_results(completion, bug_list)


if __name__ == "__main__":
    main()