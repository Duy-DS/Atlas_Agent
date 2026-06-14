import time
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from main import chunk_items, execute_batches_with_threadpool


def test_chunk_items_splits_input_into_ordered_batches():
    items = [{"qid": str(i)} for i in range(1, 6)]

    batches = list(chunk_items(items, 2))

    assert len(batches) == 3
    assert [[item["qid"] for item in batch] for batch in batches] == [["1", "2"], ["3", "4"], ["5"]]


def test_execute_batches_with_threadpool_preserves_input_order():
    batches = [
        [{"qid": "1"}],
        [{"qid": "2"}],
        [{"qid": "3"}],
    ]

    def worker(batch):
        qid = batch[0]["qid"]
        if qid == "1":
            time.sleep(0.03)
        elif qid == "2":
            time.sleep(0.01)
        else:
            time.sleep(0.02)
        return [{"qid": qid, "answer": qid}]

    results = execute_batches_with_threadpool(batches, worker, max_workers=3)

    assert [result[0]["qid"] for result in results] == ["1", "2", "3"]
