import csv
import os
import re
import sys
from io import StringIO
from pathlib import Path

from agents.agent import agent, agent_with_batch_confidences, extract_confidences
from agents.search_router import should_search
from agents.subject_router import classify_subject, should_retry_domain
from agents.web_search import WebSearchClient, default_web_search
from agents.web_search_graph import build_web_search_graph

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_QUESTION = Path(os.getenv("INPUT_CSV", BASE_DIR / "data" / "public_test_80.csv"))
PREDICTION_OUTPUT = Path(os.getenv("OUTPUT_CSV", BASE_DIR / "output" / "pred.csv"))
AUDIT_OUTPUT = Path(os.getenv("AUDIT_CSV", BASE_DIR / "output" / "pred_audit.csv"))
VALID_ANSWERS = {"A", "B", "C", "D", "N/A"}
ANSWER_RE = re.compile(r"(?:đáp án|dap an|answer).*?\b(A|B|C|D|N/A)\b", re.IGNORECASE | re.DOTALL)
ROW_RE = re.compile(r"^\s*([^,;:]+)\s*[,;:]\s*(A|B|C|D|N/A)\s*$", re.IGNORECASE)
FIELDNAMES = ["qid", "question", "A", "B", "C", "D"]
DEFAULT_BATCH_SIZE = int(os.getenv("BATCH_SIZE", "20"))
DOMAIN_PROMPT_PATHS = {
    "it": BASE_DIR / "prompts" / "domain_it.md",
    "math": BASE_DIR / "prompts" / "domain_math.md",
    "physics": BASE_DIR / "prompts" / "domain_physics.md",
    "geography": BASE_DIR / "prompts" / "domain_geography.md",
    "history": BASE_DIR / "prompts" / "domain_history.md",
    "english": BASE_DIR / "prompts" / "domain_english.md",
    "logic": BASE_DIR / "prompts" / "domain_logic.md",
    "other": BASE_DIR / "prompts" / "domain_other.md",
}
_DOMAIN_PROMPT_CACHE: dict[str, str] = {}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def question_ids(csv_text: str) -> list[str]:
    reader = csv.DictReader(StringIO(csv_text.lstrip("\ufeff")))
    return [row["qid"] for row in reader if row.get("qid")]


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


def build_predictions(question_csv: str, model_output: str) -> list[dict[str, str]]:
    answers = parse_model_answers(model_output)
    return [
        {"qid": qid, "answer": answers.get(qid, "N/A")}
        for qid in question_ids(question_csv)
    ]


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    return {(key or "").lstrip("\ufeff"): value for key, value in row.items()}


def rows_to_prompt(rows: list[dict[str, str]]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDNAMES)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in FIELDNAMES})
    return buffer.getvalue()


def batched(rows: list[dict[str, str]], batch_size: int):
    for start in range(0, len(rows), batch_size):
        yield rows[start : start + batch_size]


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


def answer_quality_for(row: dict[str, str], parsed_answers: dict[str, str], final_answers: dict[str, str]) -> str:
    qid = row.get("qid", "")
    parsed_answer = parsed_answers.get(qid)
    final_answer = final_answers.get(qid, "N/A")
    if parsed_answer in VALID_ANSWERS and parsed_answer != "N/A":
        return "clean"
    if final_answer in VALID_ANSWERS and final_answer != "N/A":
        return "weak_parse"
    if qid in parsed_answers:
        return "invalid"
    return "missing"


def predict_batch_details(rows: list[dict[str, str]]) -> tuple[dict[str, str], dict[str, str], dict[str, float]]:
    prompt = rows_to_prompt(rows)
    model_output, response = agent_with_batch_confidences(prompt)  # 1 lần gọi duy nhất
    parsed_answers = parse_model_answers(model_output)
    answers = dict(parsed_answers)
    if len(rows) == 1:
        answers = apply_single_row_fallback(rows[0], model_output, answers)
    final_answers = {row["qid"]: answers.get(row["qid"], "N/A") for row in rows if row.get("qid")}
    answer_quality = {
        row["qid"]: answer_quality_for(row, parsed_answers, final_answers)
        for row in rows
        if row.get("qid")
    }
    logprobs = extract_confidences(response, final_answers)  # extract từ response đã có
    return final_answers, answer_quality, logprobs


def predict_batch(rows: list[dict[str, str]]) -> dict[str, str]:
    answers, _, _ = predict_batch_details(rows)
    return answers


def predict_single_retry(row: dict[str, str]) -> str:
    qid = row.get("qid", "")
    model_output = agent(force_single_answer_prompt(row))
    answers = apply_single_row_fallback(row, model_output, parse_model_answers(model_output))
    return answers.get(qid, "N/A")


def domain_prompt_for(subject: str) -> str:
    normalized_subject = subject if subject in DOMAIN_PROMPT_PATHS else "other"
    if normalized_subject not in _DOMAIN_PROMPT_CACHE:
        _DOMAIN_PROMPT_CACHE[normalized_subject] = read_text(DOMAIN_PROMPT_PATHS[normalized_subject]).strip()
    return _DOMAIN_PROMPT_CACHE[normalized_subject]


def domain_retry_prompt(row: dict[str, str], subject: str) -> str:
    return domain_prompt_for(subject) + "\n\n" + rows_to_prompt([row])


def predict_domain_retry(row: dict[str, str], subject: str) -> str:
    model_output = agent(domain_retry_prompt(row, subject))
    answers = apply_single_row_fallback(row, model_output, parse_model_answers(model_output))
    return answers.get(row.get("qid", ""), "N/A")


def retry_domain_rows(
    rows: list[dict[str, str]],
    answers: dict[str, str],
    answer_quality: dict[str, str] | None = None,
) -> dict[str, str]:
    answer_quality = answer_quality or {}
    for row in rows:
        qid = row.get("qid", "")
        decision = classify_subject(row)
        if not should_retry_domain(row, answer_quality.get(qid, "clean")):
            continue
        retry_answer = predict_domain_retry(row, decision.subject)
        if retry_answer in VALID_ANSWERS:
            answers[qid] = retry_answer
    return answers



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

def retry_bad_rows(rows: list[dict[str, str]], answers: dict[str, str]) -> dict[str, str]:
    bad_rows = [row for row in rows if answers.get(row.get("qid", ""), "N/A") == "N/A"]
    for row in bad_rows:
        qid = row.get("qid", "")
        answers[qid] = predict_single_retry(row)
    return answers


def apply_web_search(
    rows: list[dict[str, str]],
    answers: dict[str, str],
    search_client: WebSearchClient,
    search_used_qids: set[str],
) -> dict[str, str]:
    for row in rows:
        qid = row.get("qid", "")
        current_answer = answers.get(qid, "N/A")
        if not should_search(row, current_answer):
            continue
        searched_answer, search_used = predict_with_search_details(row, search_client, current_answer)
        if search_used:
            search_used_qids.add(qid)
            if searched_answer != "N/A" or current_answer == "N/A":
                answers[qid] = searched_answer
    return answers


def write_predictions(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["qid", "answer"])
        writer.writeheader()
        writer.writerows(rows)



def confidence_for(row: dict[str, str], answer: str, answer_source: str = "batch", logprob: float | None = None) -> str:
    if answer == "N/A":
        return "0.00"
    if logprob is not None:
        return f"{logprob:.2f}"
    # fallback khi không có logprob
    if should_search(row, answer):
        return "0.40"
    if answer_source == "single_retry":
        return "0.55"
    if answer_source == "domain_retry_changed":
        return "0.60"
    if answer_source == "domain_retry_same":
        return "0.80"
    return "0.70"


def build_audit_rows(
    source_rows: list[dict[str, str]],
    answers: dict[str, str],
    search_used_qids: set[str] | None = None,
    answer_sources: dict[str, str] | None = None,
    logprobs: dict[str, float] | None = None,
) -> list[dict[str, str]]:
    search_used_qids = search_used_qids or set()
    answer_sources = answer_sources or {}
    logprobs = logprobs or {}
    audit_rows = []
    for row in source_rows:
        qid = row["qid"]
        answer = answers.get(qid, "N/A")
        audit_rows.append(
            {
                "qid": qid,
                "answer": answer,
                "confidence": confidence_for(row, answer, answer_sources.get(qid, "batch"), logprobs.get(qid)),
                "needs_search": "true" if should_search(row, answer) else "false",
                "search_used": "true" if qid in search_used_qids else "false",
            }
        )
    return audit_rows


def write_audit(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["qid", "answer", "confidence", "needs_search", "search_used"])
        writer.writeheader()
        writer.writerows(rows)

def run(
    input_path: Path = PUBLIC_QUESTION,
    output_path: Path = PREDICTION_OUTPUT,
    batch_size: int = DEFAULT_BATCH_SIZE,
    search_client: WebSearchClient | None = None,
    audit_output_path: Path | None = None,
    show_progress: bool = False,
) -> Path:
    with input_path.open(newline="", encoding="utf-8-sig") as f:
        source_rows = [normalize_row(row) for row in csv.DictReader(f)]
        source_rows = [row for row in source_rows if row.get("qid")]

    search_client = search_client or default_web_search()

    answers: dict[str, str] = {}
    audit_answers: dict[str, str] = {}
    answer_sources: dict[str, str] = {}
    answer_logprobs: dict[str, float] = {}
    search_used_qids: set[str] = set()
    total_rows = len(source_rows)
    processed_rows = 0
    if show_progress:
        print_progress(0, total_rows)
    for batch in batched(source_rows, batch_size):
        batch_answers, answer_quality, batch_logprobs = predict_batch_details(batch)
        answer_logprobs.update(batch_logprobs)
        for row in batch:
            qid = row.get("qid", "")
            answer_sources[qid] = "batch" if batch_answers.get(qid, "N/A") != "N/A" else "missing"

        before_single_retry = dict(batch_answers)
        batch_answers = retry_bad_rows(batch, batch_answers)
        for row in batch:
            qid = row.get("qid", "")
            if before_single_retry.get(qid, "N/A") == "N/A" and batch_answers.get(qid, "N/A") != "N/A":
                answer_sources[qid] = "single_retry"

        before_domain_retry = dict(batch_answers)
        batch_answers = retry_domain_rows(batch, batch_answers, answer_quality)
        for row in batch:
            qid = row.get("qid", "")
            if not should_retry_domain(row, answer_quality.get(qid, "clean")):
                continue
            if batch_answers.get(qid, "N/A") != before_domain_retry.get(qid, "N/A"):
                answer_sources[qid] = "domain_retry_changed"
            elif batch_answers.get(qid, "N/A") != "N/A":
                answer_sources[qid] = "domain_retry_same"

        audit_answers.update(batch_answers)
        answers.update(apply_web_search(batch, batch_answers, search_client, search_used_qids))
        processed_rows += len(batch)
        if show_progress:
            print_progress(processed_rows, total_rows)

    output_rows = [
        {"qid": row["qid"], "answer": answers.get(row["qid"], "N/A")}
        for row in source_rows
    ]
    write_predictions(output_rows, output_path)
    write_audit(build_audit_rows(source_rows, audit_answers, search_used_qids, answer_sources, answer_logprobs), audit_output_path or output_path.with_name("pred_audit.csv"))
    return output_path


if __name__ == "__main__":
    print(run(show_progress=True))
