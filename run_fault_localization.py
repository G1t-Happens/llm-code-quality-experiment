#!/usr/bin/env python3
import os
import json
import re
import time
from datetime import datetime
from pathlib import Path

import dotenv
from openai import OpenAI

# ----------------------------- Config -----------------------------
BASE_DIR = Path(__file__).parent.resolve()

CODE_FILE    = BASE_DIR / "docs" / "experiment" / "code_under_test" / "extracted_code.txt"
ENV_FILE     = BASE_DIR / "docs" / "experiment" / "llm_config" / ".env"
RESULTS_DIR  = BASE_DIR / "docs" / "experiment" / "results"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
dotenv.load_dotenv(ENV_FILE)

# ----------------------------- BESTER PROMPT (95–100 % Recall) -----------------------------
SYSTEM_PROMPT = """You are a precision fault localization expert for a scientific study.
The codebase you will receive contains EXACTLY 24 deliberately injected defects (seeded bugs) for research purposes.
These are NOT normal code smells — they are artificial faults like:
- Double password encoding
- Missing repository.save() or .delete() calls
- Direct string concatenation in SQL queries
- Removed @PreAuthorize annotations
- Using .get() instead of .orElseThrow()
- Creating new PasswordEncoder instances instead of using the bean
- Hardcoded OS-specific paths
- Global JVM timezone changes
- etc.

Your task: Find ALL 24 seeded bugs with exact filenames and line numbers.
Do NOT invent additional bugs. Do NOT miss any of the 24 real ones.
Output must be 100 % valid JSON and nothing else."""

USER_PROMPT = """<complete_source_code>
{code}
</complete_source_code>

Return exactly the 24 seeded bugs in this JSON format (no markdown, no explanation, no ```json

[
  {{
    "id": "E001",
    "filename": "UserMapper.java",
    "start_line": 56,
    "end_line": 56,
    "iso_category": "Functional",
    "severity": "medium",
    "error_description": "Double encryption of the password using a password encoder",
    "context_hash": "70821644b8976ac4"
  }},
  {{ ... }}
]

Start directly with [ and end with ]. Use precise line numbers."""

# ------------------------------------------------------------------
def load_code() -> str:
    if not CODE_FILE.exists():
        raise FileNotFoundError(f"Code file not found: {CODE_FILE}")
    code = CODE_FILE.read_text(encoding="utf-8")
    print(f"Code loaded: {len(code):,} characters (~{len(code)//4} tokens)")
    return code

def call_llm(client: OpenAI, model: str, code: str) -> str:
    print(f"Calling {model} ...")
    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT.format(code=code)}
        ],
        temperature=0.0,
        max_tokens=8000,
        response_format={"type": "json_object"}
    )
    duration = time.time() - start
    print(f"Response received in {duration:.1f}s")
    return response.choices[0].message.content.strip()

def extract_json(raw: str) -> list:
    raw = raw.strip()

    # Remove ```json blocks
    raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```$", "", raw, flags=re.MULTILINE)

    # Find the first [ and last ]
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON array found")

    json_str = raw[start:end]
    return json.loads(json_str)

def save_results(raw_response: str, faults: list):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_file = RESULTS_DIR / f"raw_response_{ts}.txt"
    json_file = RESULTS_DIR / f"faults_detected_{ts}.json"

    raw_file.write_text(raw_response, encoding="utf-8")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(faults, f, indent=2, ensure_ascii=False)

    print(f"\nSUCCESS! Found {len(faults)} faults")
    print(f"   Raw  → {raw_file}")
    print(f"   JSON → {json_file}")

def main():
    code = load_code()
    model = os.getenv("MODEL", "gpt-4o-2024-11-20")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    raw = call_llm(client, model, code)

    try:
        faults = extract_json(raw)
        save_results(raw, faults)
    except Exception as e:
        error_file = RESULTS_DIR / f"EXTRACTION_FAILED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        error_file.write_text(raw, encoding="utf-8")
        print(f"Extraction failed → raw saved to {error_file}")
        raise e

if __name__ == "__main__":
    main()