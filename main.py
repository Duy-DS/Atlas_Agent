import asyncio
import csv
import os
import time
import glob
from typing import Callable, Iterable, Iterator, List, Sequence

from src.config import load_benchmark_config


def chunk_items(items: Sequence[dict], batch_size: int) -> Iterator[List[dict]]:
    """Yield ordered batches of items."""
    if batch_size <= 0:
        batch_size = 1

    for start in range(0, len(items), batch_size):
        yield list(items[start : start + batch_size])


def format_batch_log(
    current_batch: int,
    total_batches: int,
    questions_processed: int,
    elapsed_seconds: float,
    accuracy_hits: int,
) -> str:
    safe_elapsed = max(elapsed_seconds, 0.0)
    qs_per_sec = questions_processed / safe_elapsed if safe_elapsed > 0 else float(questions_processed)
    current_acc = (accuracy_hits / questions_processed * 100.0) if questions_processed > 0 else 0.0
    return (
        f"[INFO] Processed Batch {current_batch}/{total_batches} | "
        f"Speed: {qs_per_sec:.2f} qs/sec | Acc_Estimate: {current_acc:.2f}%"
    )


def _count_valid_answers(batch_result: list) -> int:
    return sum(
        1
        for res in batch_result
        if not isinstance(res, Exception)
        and hasattr(res, "get")
        and str(res.get("answer", "")).strip().upper() in {"A", "B", "C", "D"}
    )


def _load_app_graph():
    from src.agent_graph import app_graph
    return app_graph


def _build_dataset(input_file: str) -> list[dict]:
    records: list[dict] = []

    with open(input_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            qid = row.get("qid")
            q_text = row.get("question")
            opt_a = row.get("A", "")
            opt_b = row.get("B", "")
            opt_c = row.get("C", "")
            opt_d = row.get("D", "")

            full_question = (
                f"{q_text}\n"
                f"A. {opt_a}\n"
                f"B. {opt_b}\n"
                f"C. {opt_c}\n"
                f"D. {opt_d}"
            )
            records.append({"qid": qid, "question": full_question})

    test_limit = int(os.getenv("TEST_LIMIT", "0"))
    if test_limit > 0:
        print(f"[TEST MODE] Limiting to first {test_limit} questions.")
        records = records[:test_limit]

    return records


async def _process_single_question(
    item: dict,
    app_graph,
    semaphore: asyncio.Semaphore,
    timeout_seconds: float,
) -> dict | Exception:
    async with semaphore:
        try:
            return await asyncio.wait_for(
                app_graph.ainvoke({"question": item["question"]}),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            return TimeoutError(f"Timed out after {timeout_seconds}s")
        except Exception as exc:
            return exc


async def process_dataset_async(input_file: str, output_file: str) -> None:
    print(f"Reading data from: {input_file}")
    records = _build_dataset(input_file)
    benchmark_config = load_benchmark_config()
    batch_size = benchmark_config.batch_size
    concurrency_limit = benchmark_config.concurrency_limit
    question_timeout_seconds = float(os.getenv("QUESTION_TIMEOUT_SECONDS", "60"))

    batches = list(chunk_items(records, batch_size))

    print(f"Total questions to process: {len(records)}")
    print(f"Batch size: {batch_size} | Concurrency limit: {concurrency_limit}")
    print("Processing batches with pure asyncio...")

    start_time = time.time()
    app_graph = _load_app_graph()
    total_batches = len(batches)
    progress_state = {"processed": 0, "hits": 0}

    # Initialize the semaphore inside the active event loop and respect config.
    semaphore = asyncio.Semaphore(concurrency_limit)

    results = []

    for batch_index, batch in enumerate(batches):
        tasks = [
            _process_single_question(item, app_graph, semaphore, question_timeout_seconds)
            for item in batch
        ]
        
        batch_outputs = await asyncio.gather(*tasks)
        
        for record, res in zip(batch, batch_outputs):
            results.append((record["qid"], res))
            
        progress_state["processed"] += len(batch)
        progress_state["hits"] += _count_valid_answers(batch_outputs)
        elapsed = max(time.time() - start_time, 0.0)
        
        print(
            format_batch_log(
                current_batch=batch_index + 1,
                total_batches=total_batches,
                questions_processed=progress_state["processed"],
                elapsed_seconds=elapsed,
                accuracy_hits=progress_state["hits"],
            )
        )

    end_time = time.time()
    print(f"Processed {len(records)} questions in {end_time - start_time:.2f} seconds.")

    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
    print(f"Writing output to: {output_file}")

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["qid", "answer"])

        for qid, res in results:
            if isinstance(res, Exception):
                print(f"[WARNING] Error processing qid {qid}: {res}")
                ans = "B"
            else:
                ans = res.get("answer", "B")
                if not ans:
                    ans = "B"
            writer.writerow([qid, ans])

    print("Agent pipeline finished.")


def process_dataset(input_file: str, output_file: str) -> None:
    asyncio.run(process_dataset_async(input_file, output_file))


def find_input_csv():
    if os.path.exists("/data"):
        csv_files = glob.glob("/data/*.csv")
        if csv_files:
            for f in csv_files:
                if "private_test" in f or "public_test" in f:
                    return f
            return csv_files[0]

    local_data = os.path.join(os.getcwd(), "data")
    if os.path.exists(local_data):
        csv_files = glob.glob(os.path.join(local_data, "*.csv"))
        if csv_files:
            return csv_files[0]

    return None


def get_output_csv():
    if os.path.exists("/output"):
        return "/output/pred.csv"

    return os.path.join(os.getcwd(), "output", "pred.csv")


if __name__ == "__main__":
    INPUT_CSV = find_input_csv()
    OUTPUT_CSV = get_output_csv()

    if not INPUT_CSV:
        print("Error: No CSV file found in /data or ./data")
    else:
        print(f"[CẤU HÌNH BẢNG C] - Input: {INPUT_CSV} | Output: {OUTPUT_CSV}")
        process_dataset(INPUT_CSV, OUTPUT_CSV)
