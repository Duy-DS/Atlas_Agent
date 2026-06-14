from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.config import BenchmarkConfig, load_benchmark_config
from main import format_batch_log


def test_load_benchmark_config_uses_benchmark_defaults(monkeypatch):
    monkeypatch.delenv("BATCH_SIZE", raising=False)
    monkeypatch.delenv("CONCURRENCY_LIMIT", raising=False)
    monkeypatch.delenv("LLM_CONCURRENCY_LIMIT", raising=False)
    monkeypatch.delenv("VLLM_MODEL", raising=False)

    config = load_benchmark_config()

    assert isinstance(config, BenchmarkConfig)
    assert config.batch_size == 10
    assert config.concurrency_limit == 5
    assert config.vllm_model == "Qwen/Qwen1.5-4B-Chat-AWQ"


def test_format_batch_log_handles_zero_duration():
    message = format_batch_log(current_batch=1, total_batches=4, questions_processed=10, elapsed_seconds=0.0, accuracy_hits=7)

    assert message == "[INFO] Processed Batch 1/4 | Speed: 10.00 qs/sec | Acc_Estimate: 70.00%"
