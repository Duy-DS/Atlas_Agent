import csv
import json
import os
import re
import sys
from io import StringIO
from pathlib import Path

from agents.agent import agent, raw_chat
from agents.search_router import should_search
from agents.web_search import WebSearchClient, default_web_search
from agents.web_search_graph import build_web_search_graph
from agents.workflow_v2.pipeline import run_pipeline as run_workflow_v2


def find_default_input() -> Path:
    """Find default CSV or JSON input file in data directory."""
    if "INPUT_CSV" in os.environ:
        return Path(os.getenv("INPUT_CSV"))

    data_dir = BASE_DIR / "data"
    # Look for public_test or private_test CSV/JSON files
    for name in ["public_test*.csv", "public_test*.json", "private_test*.csv", "private_test*.json"]:
        files = list(data_dir.glob(name))
        if files:
            return files[0]  # Return first match

    # Fallback to any CSV or JSON file
    for pattern in ["*.csv", "*.json"]:
        files = list(data_dir.glob(pattern))
        if files:
            return files[0]

    # Final fallback
    return BASE_DIR / "data" / "public_test.csv"

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_QUESTION = find_default_input()
PREDICTION_OUTPUT = Path(os.getenv("OUTPUT_CSV", BASE_DIR / "output" / "pred.csv"))
AUDIT_OUTPUT = Path(os.getenv("AUDIT_CSV", BASE_DIR / "output" / "pred_audit.csv"))
VALID_ANSWERS = {"A", "B", "C", "D", "N/A"}
ANSWER_RE = re.compile(r"(?:đáp án|dap an|answer).*?\b(A|B|C|D|N/A)\b", re.IGNORECASE | re.DOTALL)
ROW_RE = re.compile(r"^\s*([^,;:]+)\s*[,;:]\s*(A|B|C|D|N/A)\s*$", re.IGNORECASE)

SINGLE_RETRY_CONFIDENCE = 0.55
SEARCH_CONFIDENCE = 0.40


def parse_model_answers(model_output: str) -> dict[str, str]:
    answers = {}
    for line in (model_output or "").splitlines():
        match = ROW_RE.match(line.strip())
        if not match:
            continue
        qid, answer = match.groups()
        qid = qid.strip()
        if qid.lower() == "qid":
            continue
        answers[qid] = answer.upper()
    if answers:
        return answers

    reader = csv.DictReader(StringIO((model_output or "").strip()))
    for row in reader:
        qid = (row.get("qid") or "").strip()
        answer = (row.get("answer") or "").strip().upper()
        if qid:
            answers[qid] = answer if answer in VALID_ANSWERS else "N/A"
    return answers


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    """Normalize row and convert choices (JSON list or JSON-string) to A,B,C,D format if needed."""
    normalized = {(key or "").lstrip("﻿"): value for key, value in row.items()}

    choices = normalized.get("choices")
    if isinstance(choices, str) and choices:
        try:
            choices_str = choices.strip()
            if choices_str.startswith('[') and choices_str.endswith(']'):
                import ast
                choices = ast.literal_eval(choices_str)
                normalized["choices"] = choices
        except (ValueError, SyntaxError):
            choices = None

    if isinstance(choices, list):
        normalized['A'] = choices[0] if len(choices) > 0 else ''
        normalized['B'] = choices[1] if len(choices) > 1 else ''
        normalized['C'] = choices[2] if len(choices) > 2 else ''
        normalized['D'] = choices[3] if len(choices) > 3 else ''

    if normalized.get("qid") is not None:
        normalized["qid"] = str(normalized["qid"])

    return normalized


def load_source_rows(input_path: Path) -> list[dict[str, str]]:
    """Load rows from a CSV file or a JSON array of {qid, question, choices} objects."""
    if input_path.suffix.lower() == ".json":
        with input_path.open(encoding="utf-8-sig") as f:
            records = json.load(f)
        return [normalize_row(record) for record in records]

    with input_path.open(newline="", encoding="utf-8-sig") as f:
        return [normalize_row(row) for row in csv.DictReader(f)]


def row_choices(row: dict[str, str]) -> list[str]:
    choices = row.get("choices")
    if isinstance(choices, list):
        return [str(c) for c in choices]
    return [row[key] for key in ("A", "B", "C", "D") if row.get(key)]


def rows_to_prompt(rows: list[dict[str, str]]) -> str:
    """Render rows as a JSON array — more reliable for the LLM to parse than CSV
    when question/choice text itself contains commas or quotes."""
    payload = [
        {"qid": row.get("qid", ""), "question": row.get("question", ""), "choices": row_choices(row)}
        for row in rows
    ]
    return json.dumps(payload, ensure_ascii=False)


def print_progress(done: int, total: int, width: int = 30) -> None:
    if total <= 0:
        return
    done = min(done, total)
    filled = round(width * done / total)
    bar = "#" * filled + "-" * (width - filled)
    percent = round(100 * done / total)
    end = "\n" if done >= total else "\r"
    print(f"Progress: [{bar}] {done}/{total} ({percent}%)", end=end, file=sys.stderr, flush=True)


def extract_single_answer(model_output: str) -> str:
    matches = ANSWER_RE.findall(model_output or "")
    if not matches:
        return "N/A"
    answer = matches[-1].upper()
    return answer if answer in VALID_ANSWERS else "N/A"


def force_single_answer_prompt(row: dict[str, str]) -> str:
    return (
        "Chi tra ve dung 2 dong CSV: header qid,answer va mot dong dap an cho qid nay. "
        "Khong phan tich. answer chi la A, B, C, D hoac N/A.\n\n"
        + rows_to_prompt([row])
    )


def apply_single_row_fallback(row: dict[str, str], model_output: str, answers: dict[str, str]) -> dict[str, str]:
    qid = row.get("qid", "")
    if qid not in answers and len(answers) == 1:
        answers[qid] = next(iter(answers.values()))
    if qid not in answers:
        answers[qid] = extract_single_answer(model_output)
    return answers


def predict_single_retry(row: dict[str, str]) -> str:
    qid = row.get("qid", "")
    model_output = agent(force_single_answer_prompt(row))
    answers = apply_single_row_fallback(row, model_output, parse_model_answers(model_output))
    return answers.get(qid, "N/A")


def workflow_v2_answer(row: dict[str, str]) -> tuple[str, float, str] | None:
    def call_llm(prompt: str, **kwargs) -> str:
        return raw_chat(prompt, temperature=kwargs.get("temperature", 0.0))

    result = run_workflow_v2(row.get("question", ""), row, call_llm)
    answer = str(result.get("answer") or "N/A").strip().upper()
    if answer not in VALID_ANSWERS or answer == "N/A":
        return None
    confidence = float(result.get("confidence") or 0.0)
    if confidence <= 0.0:
        return None
    return answer, confidence, f"workflow_v2:{result.get('task', 'unknown')}"


def answer_with_search_context(row: dict[str, str], context: str) -> str:
    prompt = (
        "Dung ngu canh web de tra loi cau hoi. Chi tra ve CSV qid,answer. "
        "Khong phan tich. answer chi la A, B, C, D hoac N/A.\n\n"
        f"Ngu canh web:\n{context}\n\n"
        + rows_to_prompt([row])
    )
    model_output = agent(prompt)
    answers = apply_single_row_fallback(row, model_output, parse_model_answers(model_output))
    return answers.get(row.get("qid", ""), "N/A")


def predict_with_search_details(row: dict[str, str], search_client: WebSearchClient, answer: str = "N/A") -> tuple[str, bool]:
    graph = build_web_search_graph(search_client, answer_with_search_context)
    result = graph.invoke({"row": row, "answer": answer})
    search_used = bool(result.get("search_context"))
    return result.get("final_answer", answer), search_used


def predict_with_search(row: dict[str, str], search_client: WebSearchClient, answer: str = "N/A") -> str:
    final_answer, _ = predict_with_search_details(row, search_client, answer)
    return final_answer


def predict_row(row: dict[str, str], search_client: WebSearchClient) -> tuple[str, float, str, bool]:
    """Resolve one row: workflow_v2 first, single-retry fallback, then web search for volatile questions."""
    workflow_answer = workflow_v2_answer(row)
    if workflow_answer is not None:
        answer, confidence, source = workflow_answer
    else:
        retry_answer = predict_single_retry(row)
        if retry_answer in VALID_ANSWERS and retry_answer != "N/A":
            answer, confidence, source = retry_answer, SINGLE_RETRY_CONFIDENCE, "single_retry"
        else:
            answer, confidence, source = "N/A", 0.0, "missing"

    if should_search(row, answer):
        searched_answer, search_used = predict_with_search_details(row, search_client, answer)
        if search_used and (searched_answer != "N/A" or answer == "N/A"):
            return searched_answer, SEARCH_CONFIDENCE if searched_answer != "N/A" else 0.0, "search", True
        return answer, confidence, source, search_used

    return answer, confidence, source, False


def write_predictions(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["qid", "answer"])
        writer.writeheader()
        writer.writerows(rows)


def confidence_for(answer: str, confidence: float) -> str:
    if answer == "N/A":
        return "0.00"
    return f"{confidence:.2f}"


def build_audit_rows(
    source_rows: list[dict[str, str]],
    answers: dict[str, str],
    search_used_qids: set[str] | None = None,
    answer_sources: dict[str, str] | None = None,
    confidences: dict[str, float] | None = None,
) -> list[dict[str, str]]:
    search_used_qids = search_used_qids or set()
    answer_sources = answer_sources or {}
    confidences = confidences or {}
    audit_rows = []
    for row in source_rows:
        qid = row["qid"]
        answer = answers.get(qid, "N/A")
        audit_rows.append(
            {
                "qid": qid,
                "answer": answer,
                "confidence": confidence_for(answer, confidences.get(qid, 0.0)),
                "needs_search": "true" if should_search(row, answer) else "false",
                "search_used": "true" if qid in search_used_qids else "false",
                "answer_source": answer_sources.get(qid, "missing"),
            }
        )
    return audit_rows


def write_audit(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["qid", "answer", "confidence", "needs_search", "search_used", "answer_source"])
        writer.writeheader()
        writer.writerows(rows)


def run(
    input_path: Path = PUBLIC_QUESTION,
    output_path: Path = PREDICTION_OUTPUT,
    search_client: WebSearchClient | None = None,
    audit_output_path: Path | None = None,
    show_progress: bool = False,
) -> Path:
    source_rows = [row for row in load_source_rows(input_path) if row.get("qid")]

    search_client = search_client or default_web_search()

    answers: dict[str, str] = {}
    answer_sources: dict[str, str] = {}
    answer_confidences: dict[str, float] = {}
    search_used_qids: set[str] = set()
    total_rows = len(source_rows)
    if show_progress:
        print_progress(0, total_rows)

    for index, row in enumerate(source_rows, start=1):
        qid = row.get("qid", "")
        answer, confidence, source, search_used = predict_row(row, search_client)
        answers[qid] = answer
        answer_sources[qid] = source
        answer_confidences[qid] = confidence
        if search_used:
            search_used_qids.add(qid)
        if show_progress:
            print_progress(index, total_rows)

    output_rows = [
        {"qid": row["qid"], "answer": answers.get(row["qid"], "N/A")}
        for row in source_rows
    ]
    write_predictions(output_rows, output_path)
    write_audit(
        build_audit_rows(source_rows, answers, search_used_qids, answer_sources, answer_confidences),
        audit_output_path or output_path.with_name("pred_audit.csv"),
    )
    return output_path


if __name__ == "__main__":
    import time
    t0 = time.time()
    try:
        result = run(show_progress=True)
        elapsed = time.time() - t0
        print(f"{result} — {elapsed:.1f}s")
        print("Atlas Agent completed successfully")
        sys.exit(0)
    except Exception as e:
        print(f"Atlas Agent failed: {e}")
        sys.exit(1)
