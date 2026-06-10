import csv
import os
import re
from io import StringIO
from pathlib import Path

from agents.agent import agent

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_QUESTION = BASE_DIR / "data" / "public_test.csv"
PREDICTION_OUTPUT = BASE_DIR / "output" / "pred.csv"
VALID_ANSWERS = {"A", "B", "C", "D", "N/A"}
ANSWER_RE = re.compile(r"(?:đáp án|dap an|answer).*?\b(A|B|C|D|N/A)\b", re.IGNORECASE | re.DOTALL)
ROW_RE = re.compile(r"^\s*([^,;:]+)\s*[,;:]\s*(A|B|C|D|N/A)\s*$", re.IGNORECASE)
FIELDNAMES = ["qid", "question", "A", "B", "C", "D"]
DEFAULT_BATCH_SIZE = int(os.getenv("BATCH_SIZE", "20"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def question_ids(csv_text: str) -> list[str]:
    reader = csv.DictReader(StringIO(csv_text))
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


def retry_bad_rows(rows: list[dict[str, str]], answers: dict[str, str]) -> dict[str, str]:
    bad_rows = [row for row in rows if answers.get(row.get("qid", ""), "N/A") == "N/A"]
    for row in bad_rows:
        qid = row.get("qid", "")
        answers[qid] = predict_single_retry(row)
    return answers


def write_predictions(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["qid", "answer"])
        writer.writeheader()
        writer.writerows(rows)


def run(
    input_path: Path = PUBLIC_QUESTION,
    output_path: Path = PREDICTION_OUTPUT,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> Path:
    with input_path.open(newline="", encoding="utf-8") as f:
        source_rows = [row for row in csv.DictReader(f) if row.get("qid")]

    answers: dict[str, str] = {}
    for batch in batched(source_rows, batch_size):
        batch_answers = predict_batch(batch)
        answers.update(retry_bad_rows(batch, batch_answers))

    output_rows = [
        {"qid": row["qid"], "answer": answers.get(row["qid"], "N/A")}
        for row in source_rows
    ]
    write_predictions(output_rows, output_path)
    return output_path


if __name__ == "__main__":
    print(run())
