import csv
import os
import re
from io import StringIO
from pathlib import Path

from agents.agent import agent
from agents.search_router import should_search
from agents.web_search import WebSearchClient, default_web_search
from agents.web_search_graph import build_web_search_graph

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_QUESTION = BASE_DIR / "data" / "public_test.csv"
PREDICTION_OUTPUT = BASE_DIR / "output" / "pred.csv"
AUDIT_OUTPUT = BASE_DIR / "output" / "pred_audit.csv"
VALID_ANSWERS = {"A", "B", "C", "D", "N/A"}
ANSWER_RE = re.compile(r"(?:đáp án|dap an|answer).*?\b(A|B|C|D|N/A)\b", re.IGNORECASE | re.DOTALL)
ROW_RE = re.compile(r"^\s*([^,;:]+)\s*[,;:]\s*(A|B|C|D|N/A)\s*$", re.IGNORECASE)
FIELDNAMES = ["qid", "question", "A", "B", "C", "D"]
DEFAULT_BATCH_SIZE = int(os.getenv("BATCH_SIZE", "20"))


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


def predict_batch(rows: list[dict[str, str]]) -> dict[str, str]:
    model_output = agent(rows_to_prompt(rows))
    answers = parse_model_answers(model_output)
    if len(rows) == 1:
        answers = apply_single_row_fallback(rows[0], model_output, answers)
    return {row["qid"]: answers.get(row["qid"], "N/A") for row in rows if row.get("qid")}


def predict_single_retry(row: dict[str, str]) -> str:
    qid = row.get("qid", "")
    model_output = agent(force_single_answer_prompt(row))
    answers = apply_single_row_fallback(row, model_output, parse_model_answers(model_output))
    return answers.get(qid, "N/A")



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
            answers[qid] = searched_answer
    return answers


def write_predictions(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["qid", "answer"])
        writer.writeheader()
        writer.writerows(rows)



def confidence_for(row: dict[str, str], answer: str) -> str:
    if answer == "N/A":
        return "0.00"
    if should_search(row, answer):
        return "0.40"
    return "0.90"


def build_audit_rows(
    source_rows: list[dict[str, str]],
    answers: dict[str, str],
    search_used_qids: set[str] | None = None,
) -> list[dict[str, str]]:
    search_used_qids = search_used_qids or set()
    audit_rows = []
    for row in source_rows:
        qid = row["qid"]
        answer = answers.get(qid, "N/A")
        audit_rows.append(
            {
                "qid": qid,
                "answer": answer,
                "confidence": confidence_for(row, answer),
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
) -> Path:
    with input_path.open(newline="", encoding="utf-8-sig") as f:
        source_rows = [normalize_row(row) for row in csv.DictReader(f)]
        source_rows = [row for row in source_rows if row.get("qid")]

    search_client = search_client or default_web_search()

    answers: dict[str, str] = {}
    search_used_qids: set[str] = set()
    for batch in batched(source_rows, batch_size):
        batch_answers = predict_batch(batch)
        batch_answers = retry_bad_rows(batch, batch_answers)
        answers.update(apply_web_search(batch, batch_answers, search_client, search_used_qids))

    output_rows = [
        {"qid": row["qid"], "answer": answers.get(row["qid"], "N/A")}
        for row in source_rows
    ]
    write_predictions(output_rows, output_path)
    write_audit(build_audit_rows(source_rows, answers, search_used_qids), audit_output_path or output_path.with_name("pred_audit.csv"))
    return output_path


if __name__ == "__main__":
    print(run())
