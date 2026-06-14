from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from main import chunk_items, format_batch_log


def test_chunk_items_splits_input_into_ordered_batches():
    items = [{"qid": str(i)} for i in range(1, 6)]

    batches = list(chunk_items(items, 2))

    assert len(batches) == 3
    assert [[item["qid"] for item in batch] for batch in batches] == [["1", "2"], ["3", "4"], ["5"]]


def test_format_batch_log_handles_zero_duration():
    message = format_batch_log(
        current_batch=1,
        total_batches=4,
        questions_processed=10,
        elapsed_seconds=0.0,
        accuracy_hits=7,
    )

    assert message == "[INFO] Processed Batch 1/4 | Speed: 10.00 qs/sec | Acc_Estimate: 70.00%"
