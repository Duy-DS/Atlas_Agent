import csv
import json
import os
import re
import sys
from io import StringIO
from pathlib import Path
import collections

from agents.agent import agent
from agents.search_router import should_search
from agents.subject_router import classify_subject, should_retry_domain
from agents.web_search import WebSearchClient, default_web_search
from agents.web_search_graph import build_web_search_graph

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_QUESTION = Path(os.getenv("INPUT_CSV", BASE_DIR / "data" / "public_test.csv"))
PREDICTION_OUTPUT = Path(os.getenv("OUTPUT_CSV", BASE_DIR / "output" / "pred.csv"))
AUDIT_OUTPUT = Path(os.getenv("AUDIT_CSV", BASE_DIR / "output" / "pred_audit.csv"))
VALID_ANSWERS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ").union({"N/A"})
ANSWER_RE = re.compile(r"(?:đáp án|dap an|answer).*?\b([A-Z]|N/A)\b", re.IGNORECASE | re.DOTALL)
ROW_RE = re.compile(r"^\s*([^,;:]+)\s*[,;:]\s*([A-Z]|N/A)\s*$", re.IGNORECASE)
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
    choices_by_qid = {}
    try:
        reader = csv.DictReader(StringIO(question_csv.lstrip("\ufeff")))
        for row in reader:
            qid = row.get("qid")
            if qid:
                choices = {k for k in row.keys() if len(k) == 1 and k.isupper() and row.get(k)}
                choices_by_qid[qid] = choices
    except Exception:
        pass

    results = []
    for qid in question_ids(question_csv):
        ans = answers.get(qid, "N/A")
        if qid in choices_by_qid and ans != "N/A" and ans not in choices_by_qid[qid]:
            ans = "N/A"
        results.append({"qid": qid, "answer": ans})
    return results


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    return {(key or "").lstrip("\ufeff"): value for key, value in row.items()}


def _json_choices_to_row(item: dict) -> dict[str, str]:
    """Chuyển đổi entry JSON có field 'choices' sang dict row với A, B, C..."""
    choices = item.get("choices", [])
    labels = [chr(ord('A') + i) for i in range(len(choices))]
    row = {
        "qid": str(item.get("qid", "")),
        "question": str(item.get("question", "")),
    }
    for label, choice in zip(labels, choices):
        row[label] = str(choice)
    return row


def load_source_rows(input_path: Path) -> list[dict[str, str]]:
    """Tự động đọc cả JSON lẫn CSV, hỗ trợ choices dạng mảng."""
    suffix = input_path.suffix.lower()
    if suffix == ".json":
        with input_path.open(encoding="utf-8-sig") as f:
            data = json.load(f)
        rows = [_json_choices_to_row(item) for item in data]
        return [row for row in rows if row.get("qid")]
    else:
        with input_path.open(newline="", encoding="utf-8-sig") as f:
            rows = [normalize_row(row) for row in csv.DictReader(f)]
        return [row for row in rows if row.get("qid")]


def rows_to_prompt(rows: list[dict[str, str]]) -> str:
    if not rows: return ""
    choice_keys = sorted({k for row in rows for k in row.keys() if len(k) == 1 and k.isupper()})
    fieldnames = ["qid", "question"] + choice_keys
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def batched(rows: list[dict[str, str]], batch_size: int, max_chars: int = 1500):
    batch = []
    current_len = 0
    for row in rows:
        row_len = len(row.get("question", "")) + sum(len(row.get(k, "")) for k in row.keys() if len(k) == 1 and k.isupper())
        
        if row_len >= max_chars:
            if batch:
                yield batch
                batch = []
                current_len = 0
            yield [row]
            continue
            
        if len(batch) >= batch_size or (current_len + row_len >= max_chars and batch):
            yield batch
            batch = [row]
            current_len = row_len
        else:
            batch.append(row)
            current_len += row_len
            
    if batch:
        yield batch


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



def apply_single_row_fallback(row: dict[str, str], model_output: str, answers: dict[str, str]) -> dict[str, str]:
    qid = row.get("qid", "")
    valid_choices = {k for k in row.keys() if len(k) == 1 and k.isupper() and row.get(k)}
    if qid not in answers and len(answers) == 1:
        answers[qid] = next(iter(answers.values()))
    if qid not in answers:
        answers[qid] = extract_single_answer(model_output)
    ans = answers.get(qid, "N/A")
    if ans != "N/A" and valid_choices and ans not in valid_choices:
        answers[qid] = "N/A"
    return answers


def force_single_answer_prompt(row: dict[str, str]) -> str:
    return (
        "Chi tra ve dung 2 dong CSV: header qid,answer va mot dong dap an cho qid nay. "
        "Khong phan tich. answer chi la A, B, C... hoac N/A.\n\n"
        + rows_to_prompt([row])
    )

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


def predict_batch_details(rows: list[dict[str, str]], force_think: bool = False, n_samples: int = 3) -> tuple[dict[str, str], dict[str, str], dict[str, float]]:
    prompt = "Chỉ trả về định dạng CSV có qid,answer. Khong giai thich.\n\n" + rows_to_prompt(rows)
    all_answers = []
    parsed_original = {}
    
    for _ in range(n_samples):
        model_output = agent(prompt, think=force_think, temperature=0.4 if n_samples > 1 else 0.0)
        parsed = parse_model_answers(model_output)
        parsed_original = dict(parsed)
        if len(rows) == 1:
            parsed = apply_single_row_fallback(rows[0], model_output, parsed)
        all_answers.append(parsed)

    final_answers = {}
    confidence = {}
    for row in rows:
        qid = row.get("qid", "")
        votes = [ans.get(qid, "N/A") for ans in all_answers]
        valid_choices = {k for k in row.keys() if len(k) == 1 and k.isupper() and row.get(k)}
        valid_votes = [v for v in votes if v in VALID_ANSWERS and v != "N/A" and (not valid_choices or v in valid_choices)]
        
        if not valid_votes:
            final_answers[qid] = "N/A"
            confidence[qid] = 0.0
            continue
            
        counts = collections.Counter(valid_votes)
        best_answer, best_count = counts.most_common(1)[0]
        final_answers[qid] = best_answer
        confidence[qid] = best_count / n_samples

    last_parsed = parsed_original if len(rows) == 1 else (all_answers[-1] if all_answers else {})
    answer_quality = {
        row["qid"]: answer_quality_for(row, last_parsed, final_answers)
        for row in rows
        if row.get("qid")
    }
    return final_answers, answer_quality, confidence


def predict_batch(rows: list[dict[str, str]]) -> dict[str, str]:
    answers, _, _ = predict_batch_details(rows)
    return answers


def predict_single_retry(row: dict[str, str]) -> str:
    qid = row.get("qid", "")
    model_output = agent(force_single_answer_prompt(row), think=True)
    answers = apply_single_row_fallback(row, model_output, parse_model_answers(model_output))
    return answers.get(qid, "N/A")


def domain_prompt_for(subject: str) -> str:
    normalized_subject = subject if subject in DOMAIN_PROMPT_PATHS else "other"
    if normalized_subject not in _DOMAIN_PROMPT_CACHE:
        _DOMAIN_PROMPT_CACHE[normalized_subject] = read_text(DOMAIN_PROMPT_PATHS[normalized_subject]).strip()
    return _DOMAIN_PROMPT_CACHE[normalized_subject]


def domain_retry_prompt(row: dict[str, str], subject: str) -> str:
    return domain_prompt_for(subject) + "\n\n" + rows_to_prompt([row])


def predict_domain_retry(row: dict[str, str], subject: str) -> tuple[str, float]:
    prompt = domain_retry_prompt(row, subject)
    results = []
    for _ in range(1):
        model_output = agent(prompt, think=True, temperature=0.4)
        answers = apply_single_row_fallback(row, model_output, parse_model_answers(model_output))
        answer = answers.get(row.get("qid", ""), "N/A")
        results.append(answer)
    
    valid_results = [r for r in results if r in VALID_ANSWERS and r != "N/A"]
    if not valid_results:
        return "N/A", 0.0
    
    counter = collections.Counter(valid_results)
    best_answer, count = counter.most_common(1)[0]
    return best_answer, count / 1.0


def retry_domain_rows(
    rows: list[dict[str, str]],
    answers: dict[str, str],
    answer_quality: dict[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, float]]:
    answer_quality = answer_quality or {}
    domain_confidences = {}
    for row in rows:
        qid = row.get("qid", "")
        decision = classify_subject(row)
        if not should_retry_domain(row, answer_quality.get(qid, "clean")):
            continue
        retry_answer, ratio = predict_domain_retry(row, decision.subject)
        if retry_answer in VALID_ANSWERS:
            answers[qid] = retry_answer
            domain_confidences[qid] = ratio
    return answers, domain_confidences



def answer_with_search_context(row: dict[str, str], context: str) -> str:
    prompt = (
        "Dung ngu canh web de tra loi cau hoi. Chi tra ve CSV qid,answer. "
        "Khong phan tich. answer chi la A, B, C... hoac N/A.\n\n"
        f"Ngu canh web:\n{context}\n\n"
        + rows_to_prompt([row])
    )
    model_output = agent(prompt)
    answers = apply_single_row_fallback(row, model_output, parse_model_answers(model_output))
    return answers.get(row.get("qid", ""), "N/A")


def extract_search_keywords(question: str) -> str:
    if not question:
        return ""
    prompt = (
        "Trích xuất từ khóa tìm kiếm Google cho câu hỏi sau. "
        "Chỉ trả về cụm từ khóa ngắn gọn, không giải thích, không bao gồm các đáp án.\n\n"
        f"Câu hỏi: {question}"
    )
    keyword = agent(prompt, think=False)
    return keyword.strip()


def predict_with_search_details(row: dict[str, str], search_client: WebSearchClient, answer: str = "N/A") -> tuple[str, bool]:
    graph = build_web_search_graph(search_client, answer_with_search_context, extract_search_keywords)
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



def confidence_for(row: dict[str, str], answer: str, answer_source: str = "batch", domain_ratio: float = None) -> str:
    if answer == "N/A":
        return "0.00"
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
    domain_confidences: dict[str, float] | None = None,
) -> list[dict[str, str]]:
    search_used_qids = search_used_qids or set()
    answer_sources = answer_sources or {}
    domain_confidences = domain_confidences or {}
    audit_rows = []
    for row in source_rows:
        qid = row["qid"]
        answer = answers.get(qid, "N/A")
        audit_rows.append(
            {
                "qid": qid,
                "answer": answer,
                "confidence": confidence_for(row, answer, answer_sources.get(qid, "batch"), domain_confidences.get(qid)),
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
    samples: int = 1,
) -> Path:
    source_rows = load_source_rows(input_path)

    search_client = search_client or default_web_search()

    answers: dict[str, str] = {}
    audit_answers: dict[str, str] = {}
    answer_sources: dict[str, str] = {}
    domain_confidences: dict[str, float] = {}
    search_used_qids: set[str] = set()
    total_rows = len(source_rows)
    processed_rows = 0

    if show_progress:
        print_progress(0, total_rows)

    for batch in batched(source_rows, batch_size):
        # --- Bước 1: Dự đoán batch (bật think cho câu dài) ---
        is_long_context = len(batch) == 1 and (
            len(batch[0].get("question", "")) +
            sum(len(batch[0].get(k, "")) for k in batch[0].keys() if len(k) == 1 and k.isupper())
        ) >= 1500
        batch_answers, answer_quality, answer_confidence = predict_batch_details(batch, force_think=is_long_context, n_samples=samples)

        for row in batch:
            qid = row.get("qid", "")
            answer_sources[qid] = "batch" if batch_answers.get(qid, "N/A") != "N/A" else "missing"

        # --- Bước 2: Retry N/A ---
        before_single_retry = dict(batch_answers)
        batch_answers = retry_bad_rows(batch, batch_answers)
        for row in batch:
            qid = row.get("qid", "")
            if before_single_retry.get(qid, "N/A") == "N/A" and batch_answers.get(qid, "N/A") != "N/A":
                answer_sources[qid] = "single_retry"
        # confidence‑driven retry for low‑confidence N/A answers
        for row in batch:
            qid = row.get("qid", "")
            if batch_answers.get(qid, "N/A") == "N/A" and answer_confidence.get(qid, 0.0) < 0.6:
                retry_ans = predict_single_retry(row)
                if retry_ans != "N/A":
                    batch_answers[qid] = retry_ans
                    answer_sources[qid] = "confidence_retry"

        # --- Bước 3: Domain retry ---
        before_domain_retry = dict(batch_answers)
        batch_answers, domain_confs = retry_domain_rows(batch, batch_answers, answer_quality)
        domain_confidences.update(domain_confs)
        for row in batch:
            qid = row.get("qid", "")
            if not should_retry_domain(row, answer_quality.get(qid, "clean")):
                continue
            if batch_answers.get(qid, "N/A") != before_domain_retry.get(qid, "N/A"):
                answer_sources[qid] = "domain_retry_changed"
            elif batch_answers.get(qid, "N/A") != "N/A":
                answer_sources[qid] = "domain_retry_same"

        # --- Bước 4: Fallback cuối - chọn A nếu vẫn N/A ---
        for row in batch:
            qid = row.get("qid", "")
            if batch_answers.get(qid, "N/A") == "N/A":
                # choose the available option with the longest content as heuristic
                available = [k for k in row.keys() if len(k) == 1 and k.isupper() and row.get(k)]
                if available:
                    best = max(available, key=lambda k: len(row.get(k, "")))
                    batch_answers[qid] = best
                    answer_sources[qid] = "fallback_best"
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
    write_audit(build_audit_rows(source_rows, audit_answers, search_used_qids, answer_sources, domain_confidences), audit_output_path or output_path.with_name("pred_audit.csv"))
    return output_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=None, help="Path to input CSV or JSON file")
    parser.add_argument("--output", default=None, help="Path to output pred.csv")
    parser.add_argument("--samples", type=int, default=3, help="Self‑consistency samples per batch")
    args = parser.parse_args()

    run_kwargs = {"show_progress": True, "samples": args.samples}
    if args.input:
        run_kwargs["input_path"] = Path(args.input)
    elif os.getenv("INPUT_CSV"):
        run_kwargs["input_path"] = Path(os.getenv("INPUT_CSV"))
    if args.output:
        run_kwargs["output_path"] = Path(args.output)
    elif os.getenv("OUTPUT_CSV"):
        run_kwargs["output_path"] = Path(os.getenv("OUTPUT_CSV"))
    # cap batch size when web search is enabled to keep token budget safe
    if os.getenv("WEB_SEARCH_ENABLED", "false").lower() == "true":
        run_kwargs["batch_size"] = min(run_kwargs.get("batch_size", DEFAULT_BATCH_SIZE), 10)
    print(run(**run_kwargs))
