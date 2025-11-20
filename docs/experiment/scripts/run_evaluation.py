#!/usr/bin/env python3
import json
import csv
import asyncio
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# ========================= SETUP =========================
console = Console()
BASE_DIR = Path(__file__).parent.parent  # docs/experiment/
CODE_FILE = BASE_DIR / "code_under_test" / "extracted_code.txt"
GROUND_TRUTH_CSV = BASE_DIR / "ground_truth" / "seeded_errors_iso25010.csv"
PROMPT_TEMPLATE = BASE_DIR / "llm_config" / "prompt_fault_localization.txt"
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / "llm_config" / ".env")

LINE_TOLERANCE = 1

# ========================= DATACLASSES =========================
@dataclass(frozen=True)
class GroundTruthBug:
    id: str
    filename: str
    start_line: int
    end_line: int
    iso_category: str
    description: str
    severity: str

@dataclass
class DetectedBug:
    filename: str
    start_line: int
    end_line: int
    description: str
    raw: dict

# ========================= LOADERS =========================
def load_ground_truth() -> List[GroundTruthBug]:
    bugs = []
    with open(GROUND_TRUTH_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bugs.append(GroundTruthBug(
                id=row["id"],
                filename=row["filename"],
                start_line=int(row["start_line"]),
                end_line=int(row["end_line"]),
                iso_category=row["iso_category"],
                description=row["error_description"],
                severity=row["severity"]
            ))
    console.log(f"[green]✓ Loaded {len(bugs)} ground-truth bugs[/green]")
    return bugs

def load_project_code() -> str:
    code = CODE_FILE.read_text(encoding="utf-8")
    line_count = len(code.splitlines())
    console.log(f"[green]✓ Loaded project code ({line_count} lines)[/green]")
    return code

def build_prompt(code: str) -> str:
    template = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    return template.replace("{{CODE_BLOCK}}", code)

# ========================= LLM CALL =========================
async def call_openai(prompt: str) -> List[DetectedBug]:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }

    async with httpx.AsyncClient(timeout=240.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        # Robustes Extrahieren des JSON-Arrays
        json_str = content.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.endswith("```"):
            json_str = json_str[:-3].strip()

        try:
            data = json.loads(json_str)
            if not isinstance(data, list):
                raise ValueError("LLM returned JSON but not an array")
        except json.JSONDecodeError as e:
            console.log(f"[red]JSON parsing error:[/red] {e}")
            console.log(f"Raw LLM output:\n{content}")
            raise

        bugs = []
        for item in data:
            bugs.append(DetectedBug(
                filename=item["filename"],
                start_line=int(item["start_line"]),
                end_line=int(item["end_line"]),
                description=item["description"],
                raw=item
            ))
        return bugs

# ========================= EVALUATION =========================
def lines_overlap(a_s: int, a_e: int, b_s: int, b_e: int) -> bool:
    return (a_s <= b_e + LINE_TOLERANCE) and (a_e >= b_s - LINE_TOLERANCE)

def evaluate(tp_gt: List[GroundTruthBug], detected: List[DetectedBug]):
    matched_gt = set()
    fp = []
    for det in detected:
        match = False
        for gt in tp_gt:
            if (det.filename == gt.filename and
                    lines_overlap(gt.start_line, gt.end_line, det.start_line, det.end_line)):
                matched_gt.add(gt)
                match = True
                break
        if not match:
            fp.append(det)

    fn = [gt for gt in tp_gt if gt not in matched_gt]
    tp = list(matched_gt)

    return tp, fp, fn

# ========================= MAIN =========================
async def main():
    console.print("[bold magenta]LLM Fault Localization Experiment[/bold magenta]\n")

    ground_truth = load_ground_truth()
    code = load_project_code()
    prompt = build_prompt(code)

    with Progress(SpinnerColumn(), TextColumn("[cyan]Querying LLM..."), console=console) as progress:
        task = progress.add_task("Calling model", total=None)
        try:
            detected = await call_openai(prompt)
        except Exception as e:
            console.print(f"[red]✗ LLM call failed: {e}[/red]")
            return
        finally:
            progress.update(task, completed=True)

    tp, fp, fn = evaluate(ground_truth, detected)

    precision = len(tp) / (len(tp) + len(fp)) if (tp or fp) else 0.0
    recall = len(tp) / len(ground_truth)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    result = {
        "model": os.getenv("OPENAI_MODEL"),
        "total_ground_truth": len(ground_truth),
        "true_positives": len(tp),
        "false_positives": len(fp),
        "false_negatives": len(fn),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp_ids": sorted([bug.id for bug in tp]),
        "fn_ids": sorted([bug.id for bug in fn]),
        "fp_details": [b.raw for b in fp],
        "detected_raw": [b.raw for b in detected]
    }

    timestamp = int(asyncio.get_event_loop().time())
    model_clean = os.getenv("OPENAI_MODEL").replace("/", "_")
    outfile = RESULTS_DIR / f"result_{model_clean}_{timestamp}.json"
    outfile.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    console.rule("[bold green]Evaluation Complete")
    console.print(f"Model:        [bold]{result['model']}[/bold]")
    console.print(f"TP:           [green]{len(tp)}[/green] → {', '.join(result['tp_ids'])}")
    console.print(f"FP:           [red]{len(fp)}[/red]")
    console.print(f"FN:           [yellow]{len(fn)}[/yellow] → {', '.join(result['fn_ids'])}")
    console.print(f"Precision:    [bold]{result['precision']:.4f}[/bold]")
    console.print(f"Recall:       [bold]{result['recall']:.4f}[/bold]")
    console.print(f"F1-Score:     [bold]{result['f1']:.4f}[/bold]")
    console.print(f"\n→ Results saved to: [cyan]{outfile}[/cyan]\n")

if __name__ == "__main__":
    asyncio.run(main())