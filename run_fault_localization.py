#!/usr/bin/env python3
import json
import time
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List

import dotenv
from openai import OpenAI
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

# ----------------------------- Pydantic Schema -----------------------------
class SeededBug(BaseModel):
    filename: str = Field(..., description="Java filename")
    start_line: int = Field(..., ge=1, description="Start line")
    end_line: int = Field(..., ge=1, description="End line")
    severity: str = Field(..., pattern="^(critical|high|medium|low)$")
    error_description: str = Field(..., description="Precise bug description")

class BugList(BaseModel):
    bugs: List[SeededBug]

# ----------------------------- Prompts -----------------------------
SYSTEM_PROMPT = (BASE_DIR / SYSTEM_PROMPT_FILE).read_text(encoding="utf-8").strip()
USER_PROMPT_TEMPLATE = (BASE_DIR / USER_PROMPT_FILE).read_text(encoding="utf-8").strip()

# ----------------------------- Code -----------------------------
def load_code() -> str:
    code = CODE_FILE.read_text(encoding="utf-8")
    print(f"Code loaded: {len(code):,} chars | MD5: {hashlib.md5(code.encode()).hexdigest()}")
    return code

# ----------------------------- Structured Outputs Call -----------------------------
def call_llm(client: OpenAI, model: str, code: str):
    user_msg = USER_PROMPT_TEMPLATE.format(code=code)

    print(f"Calling {model} with Structured Outputs (.parse()) ...")
    start = time.time()

    # OpenAI-API-Call
    completion = client.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.3,
        max_tokens=32768,
        response_format=BugList
    )

    duration = time.time() - start
    print(f"Response received in {duration:.1f}s")
    return completion

# ----------------------------- Save -----------------------------
def save_results(completion, bugs: List[dict]):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_file = RESULTS_DIR / f"raw_response_{ts}.txt"
    json_file = RESULTS_DIR / f"faults_detected_{ts}.json"

    raw_file.write_text(completion.model_dump_json(indent=2), encoding="utf-8")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(bugs, f, indent=2, ensure_ascii=False)

    print(f"\nSUCCESS! Found {len(bugs)} seeded bugs")
    print(f"   Raw  → {raw_file}")
    print(f"   JSON → {json_file}")

# ----------------------------- Main -----------------------------
def main():
    code = load_code()
    model = os.getenv("OPENAI_MODEL", "gpt-4.1")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    completion = call_llm(client, model, code)

    # Structured Outputs
    parsed: BugList = completion.choices[0].message.parsed
    bug_list = [bug.model_dump() for bug in parsed.bugs]

    save_results(completion, bug_list)

if __name__ == "__main__":
    main()