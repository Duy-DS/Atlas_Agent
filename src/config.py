from dataclasses import dataclass
import os


@dataclass(frozen=True)
class BenchmarkConfig:
    batch_size: int = 10
    concurrency_limit: int = 5
    vllm_model: str = "Qwen/Qwen1.5-4B-Chat-AWQ"
    served_model_name: str = "qwen-hackathon"
    gpu_memory_utilization: float = 0.9
    swap_space: int = 4


def _read_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _read_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def load_benchmark_config() -> BenchmarkConfig:
    batch_size = _read_int("BATCH_SIZE", 10)
    concurrency_limit = _read_int("CONCURRENCY_LIMIT", _read_int("LLM_CONCURRENCY_LIMIT", 5))

    return BenchmarkConfig(
        batch_size=batch_size if batch_size > 0 else 10,
        concurrency_limit=concurrency_limit if concurrency_limit > 0 else 5,
        vllm_model=os.getenv("VLLM_MODEL", "Qwen/Qwen1.5-4B-Chat-AWQ"),
        served_model_name=os.getenv("VLLM_SERVED_MODEL_NAME", "qwen-hackathon"),
        gpu_memory_utilization=_read_float("VLLM_GPU_MEMORY_UTILIZATION", 0.9),
        swap_space=_read_int("VLLM_SWAP_SPACE", 4),
    )
