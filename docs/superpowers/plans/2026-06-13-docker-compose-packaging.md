# Docker Compose Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package Atlas Agent so a user can run the Python pipeline plus Ollama with Docker Compose on CPU or GPU and get outputs in `output/`.

**Architecture:** Keep the app image small and Python-only, run Ollama as a separate Compose service, and connect the app to Ollama over the Compose network using `OLLAMA_BASE_URL=http://ollama:11434`. Use bind mounts for `data/`, `output/`, and Ollama model cache so input/output and model downloads survive container restarts.

**Tech Stack:** Docker, Docker Compose, Python 3.11 slim, Ollama, LangChain/LangGraph, pandas.

---

## File Structure

- Modify `main.py`: read default input/output paths from environment variables so Docker and local runs use the same code path.
- Modify `entrypoints.sh`: validate the configured input file, create the output directory, optionally wait for Ollama, then run `python /app/main.py`.
- Modify `Dockerfile`: add curl for health/wait checks and keep dependency install cache-friendly.
- Modify `docker-compose.yml`: define the CPU Compose stack, app volumes, environment defaults, Ollama healthcheck, and one-shot model pull.
- Modify `docker-compose.gpu.yml`: keep only GPU-specific overrides for the Ollama service.
- Create `.env.example`: document runtime knobs that Compose already consumes.
- Modify `.dockerignore`: keep Docker context lean while ensuring required app source and prompts remain included.
- Modify `README.md`: add exact CPU/GPU run commands and expected output files.
- Add `tests/test_docker_config.py`: verify Compose-facing defaults in Python/entrypoint files without requiring Docker daemon in unit tests.

## Task 1: Make Runtime Paths Configurable

**Files:**
- Modify: `main.py`
- Test: `tests/test_docker_config.py`

- [ ] **Step 1: Add failing tests for environment-driven default paths**

Create `tests/test_docker_config.py` with:

```python
import importlib
from pathlib import Path


def test_main_uses_environment_default_paths(monkeypatch, tmp_path):
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "answers.csv"
    audit_path = tmp_path / "audit.csv"

    monkeypatch.setenv("INPUT_CSV", str(input_path))
    monkeypatch.setenv("OUTPUT_CSV", str(output_path))
    monkeypatch.setenv("AUDIT_CSV", str(audit_path))

    import main

    reloaded = importlib.reload(main)

    assert reloaded.PUBLIC_QUESTION == input_path
    assert reloaded.PREDICTION_OUTPUT == output_path
    assert reloaded.AUDIT_OUTPUT == audit_path
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
rtk pytest tests/test_docker_config.py::test_main_uses_environment_default_paths -q
```

Expected: FAIL because `main.py` currently hardcodes `BASE_DIR / "data" / "public_test_80.csv"` and output paths.

- [ ] **Step 3: Implement environment defaults in `main.py`**

Replace the current three path constants:

```python
PUBLIC_QUESTION = BASE_DIR / "data" / "public_test_80.csv"
PREDICTION_OUTPUT = BASE_DIR / "output" / "pred.csv"
AUDIT_OUTPUT = BASE_DIR / "output" / "pred_audit.csv"
```

with:

```python
PUBLIC_QUESTION = Path(os.getenv("INPUT_CSV", BASE_DIR / "data" / "public_test.csv"))
PREDICTION_OUTPUT = Path(os.getenv("OUTPUT_CSV", BASE_DIR / "output" / "pred.csv"))
AUDIT_OUTPUT = Path(os.getenv("AUDIT_CSV", BASE_DIR / "output" / "pred_audit.csv"))
```

- [ ] **Step 4: Verify the path test passes**

Run:

```bash
rtk pytest tests/test_docker_config.py::test_main_uses_environment_default_paths -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add main.py tests/test_docker_config.py
rtk git commit -m "chore: make runtime paths configurable"
```

## Task 2: Harden the Docker Entrypoint

**Files:**
- Modify: `entrypoints.sh`
- Test: `tests/test_docker_config.py`

- [ ] **Step 1: Add failing entrypoint content test**

Append to `tests/test_docker_config.py`:

```python
def test_entrypoint_uses_configured_paths_and_waits_for_ollama():
    entrypoint = Path("entrypoints.sh").read_text(encoding="utf-8")

    assert "${INPUT_CSV:-/data/public_test.csv}" in entrypoint
    assert "${OUTPUT_CSV:-/output/pred.csv}" in entrypoint
    assert "mkdir -p \"$(dirname \"$OUTPUT_CSV\")\"" in entrypoint
    assert "OLLAMA_BASE_URL" in entrypoint
    assert "/api/tags" in entrypoint
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
rtk pytest tests/test_docker_config.py::test_entrypoint_uses_configured_paths_and_waits_for_ollama -q
```

Expected: FAIL because the entrypoint currently checks `/data/public_test.csv` and `/data/private_test.csv` directly and does not create `/output`.

- [ ] **Step 3: Replace `entrypoints.sh` content**

Use this exact script:

```sh
#!/bin/sh
set -e

INPUT_CSV="${INPUT_CSV:-/data/public_test.csv}"
OUTPUT_CSV="${OUTPUT_CSV:-/output/pred.csv}"
AUDIT_CSV="${AUDIT_CSV:-/output/pred_audit.csv}"
APP_MODE="${APP_MODE:-python}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://ollama:11434}"

echo "Starting Atlas Agent..."
echo "Input: ${INPUT_CSV}"
echo "Output: ${OUTPUT_CSV}"
echo "Audit: ${AUDIT_CSV}"

if [ ! -f "$INPUT_CSV" ]; then
  echo "ERROR: input CSV not found: $INPUT_CSV"
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_CSV")"
mkdir -p "$(dirname "$AUDIT_CSV")"

if [ "${WAIT_FOR_OLLAMA:-true}" = "true" ]; then
  echo "Waiting for Ollama at ${OLLAMA_BASE_URL}..."
  until curl -fsS "${OLLAMA_BASE_URL}/api/tags" >/dev/null; do
    sleep 2
  done
fi

export INPUT_CSV OUTPUT_CSV AUDIT_CSV OLLAMA_BASE_URL

if [ "$APP_MODE" = "streamlit" ]; then
  echo "Starting Streamlit..."
  exec streamlit run /app/main.py --server.address=0.0.0.0 --server.port=8501
fi

echo "Running main.py..."
exec python /app/main.py
```

- [ ] **Step 4: Verify entrypoint test passes**

Run:

```bash
rtk pytest tests/test_docker_config.py::test_entrypoint_uses_configured_paths_and_waits_for_ollama -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add entrypoints.sh tests/test_docker_config.py
rtk git commit -m "chore: harden docker entrypoint"
```

## Task 3: Update Docker Image Definition

**Files:**
- Modify: `Dockerfile`
- Test: `tests/test_docker_config.py`

- [ ] **Step 1: Add failing Dockerfile test**

Append to `tests/test_docker_config.py`:

```python
def test_dockerfile_installs_curl_and_uses_entrypoint():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "apt-get update" in dockerfile
    assert "apt-get install -y --no-install-recommends curl" in dockerfile
    assert 'ENTRYPOINT ["/app/entrypoints.sh"]' in dockerfile
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
rtk pytest tests/test_docker_config.py::test_dockerfile_installs_curl_and_uses_entrypoint -q
```

Expected: FAIL because the current image does not install curl.

- [ ] **Step 3: Replace `Dockerfile` content**

Use:

```Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chmod +x /app/entrypoints.sh

ENTRYPOINT ["/app/entrypoints.sh"]
```

- [ ] **Step 4: Verify Dockerfile test passes**

Run:

```bash
rtk pytest tests/test_docker_config.py::test_dockerfile_installs_curl_and_uses_entrypoint -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add Dockerfile tests/test_docker_config.py
rtk git commit -m "chore: prepare app image for compose runtime"
```

## Task 4: Normalize Docker Compose CPU Stack

**Files:**
- Modify: `docker-compose.yml`
- Test: `tests/test_docker_config.py`

- [ ] **Step 1: Add failing Compose content test**

Append to `tests/test_docker_config.py`:

```python
def test_compose_defines_cpu_stack_with_healthcheck_and_outputs():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "atlas-ollama" in compose
    assert "atlas-agent" in compose
    assert "healthcheck:" in compose
    assert "condition: service_healthy" in compose
    assert "./data:/data:ro" in compose
    assert "./output:/output" in compose
    assert "INPUT_CSV=${INPUT_CSV:-/data/public_test.csv}" in compose
    assert "OUTPUT_CSV=${OUTPUT_CSV:-/output/pred.csv}" in compose
    assert "AUDIT_CSV=${AUDIT_CSV:-/output/pred_audit.csv}" in compose
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
rtk pytest tests/test_docker_config.py::test_compose_defines_cpu_stack_with_healthcheck_and_outputs -q
```

Expected: FAIL because the current Compose file uses different container names and does not mount `./output:/output`.

- [ ] **Step 3: Replace `docker-compose.yml` content**

Use:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: atlas-ollama
    restart: unless-stopped
    ports:
      - "${OLLAMA_HOST_PORT:-11435}:11434"
    volumes:
      - ./ollama-data:/root/.ollama
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 10s
      timeout: 5s
      retries: 30
      start_period: 10s

  ollama-pull:
    image: curlimages/curl:latest
    container_name: atlas-ollama-pull
    depends_on:
      ollama:
        condition: service_healthy
    environment:
      - MODEL_NAME=${MODEL_NAME:-qwen3.5:0.8b}
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        curl -fsS -X POST http://ollama:11434/api/pull \
          -H 'Content-Type: application/json' \
          -d "{\"name\":\"${MODEL_NAME}\"}"
    restart: "no"

  app:
    build:
      context: .
    container_name: atlas-agent
    depends_on:
      ollama:
        condition: service_healthy
      ollama-pull:
        condition: service_completed_successfully
    volumes:
      - ./data:/data:ro
      - ./output:/output
      - ./chroma-data:/app/chroma-data
    environment:
      - PYTHONUNBUFFERED=1
      - OLLAMA_BASE_URL=http://ollama:11434
      - MODEL_NAME=${MODEL_NAME:-qwen3.5:0.8b}
      - BATCH_SIZE=${BATCH_SIZE:-20}
      - OLLAMA_NUM_PREDICT=${OLLAMA_NUM_PREDICT:-512}
      - WEB_SEARCH_ENABLED=${WEB_SEARCH_ENABLED:-false}
      - WEB_SEARCH_PROVIDER=${WEB_SEARCH_PROVIDER:-duckduckgo}
      - WEB_SEARCH_ENDPOINT=${WEB_SEARCH_ENDPOINT:-}
      - INPUT_CSV=${INPUT_CSV:-/data/public_test.csv}
      - OUTPUT_CSV=${OUTPUT_CSV:-/output/pred.csv}
      - AUDIT_CSV=${AUDIT_CSV:-/output/pred_audit.csv}
      - WAIT_FOR_OLLAMA=true
      - APP_MODE=python
    restart: "no"
```

- [ ] **Step 4: Verify Compose content test passes**

Run:

```bash
rtk pytest tests/test_docker_config.py::test_compose_defines_cpu_stack_with_healthcheck_and_outputs -q
```

Expected: PASS.

- [ ] **Step 5: Validate Compose syntax**

Run:

```bash
rtk docker compose config
```

Expected: command exits 0 and prints resolved services `ollama`, `ollama-pull`, and `app`.

- [ ] **Step 6: Commit**

```bash
rtk git add docker-compose.yml tests/test_docker_config.py
rtk git commit -m "chore: normalize docker compose cpu stack"
```

## Task 5: Keep GPU Override Focused

**Files:**
- Modify: `docker-compose.gpu.yml`
- Test: `tests/test_docker_config.py`

- [ ] **Step 1: Add GPU override test**

Append to `tests/test_docker_config.py`:

```python
def test_gpu_compose_only_overrides_ollama_gpu_runtime():
    gpu_compose = Path("docker-compose.gpu.yml").read_text(encoding="utf-8")

    assert "ollama:" in gpu_compose
    assert "driver: nvidia" in gpu_compose
    assert "NVIDIA_VISIBLE_DEVICES=all" in gpu_compose
    assert "app:" not in gpu_compose
```

- [ ] **Step 2: Run the GPU override test**

Run:

```bash
rtk pytest tests/test_docker_config.py::test_gpu_compose_only_overrides_ollama_gpu_runtime -q
```

Expected: PASS if the current GPU override remains focused. If it fails, replace the file in Step 3.

- [ ] **Step 3: Normalize `docker-compose.gpu.yml` only if the test fails**

Use:

```yaml
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities:
                - gpu
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
```

- [ ] **Step 4: Validate combined GPU Compose syntax**

Run:

```bash
rtk docker compose -f docker-compose.yml -f docker-compose.gpu.yml config
```

Expected: command exits 0 and the resolved `ollama` service includes NVIDIA device reservations.

- [ ] **Step 5: Commit**

```bash
rtk git add docker-compose.gpu.yml tests/test_docker_config.py
rtk git commit -m "chore: document gpu compose override"
```

## Task 6: Add Environment Example

**Files:**
- Create: `.env.example`
- Test: `tests/test_docker_config.py`

- [ ] **Step 1: Add failing `.env.example` test**

Append to `tests/test_docker_config.py`:

```python
def test_env_example_documents_compose_runtime_knobs():
    env_example = Path(".env.example").read_text(encoding="utf-8")

    assert "MODEL_NAME=qwen3.5:0.8b" in env_example
    assert "BATCH_SIZE=20" in env_example
    assert "OLLAMA_NUM_PREDICT=512" in env_example
    assert "INPUT_CSV=/data/public_test.csv" in env_example
    assert "OUTPUT_CSV=/output/pred.csv" in env_example
    assert "AUDIT_CSV=/output/pred_audit.csv" in env_example
    assert "WEB_SEARCH_ENABLED=false" in env_example
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
rtk pytest tests/test_docker_config.py::test_env_example_documents_compose_runtime_knobs -q
```

Expected: FAIL because `.env.example` does not exist yet.

- [ ] **Step 3: Create `.env.example`**

Use:

```dotenv
MODEL_NAME=qwen3.5:0.8b
BATCH_SIZE=20
OLLAMA_NUM_PREDICT=512

INPUT_CSV=/data/public_test.csv
OUTPUT_CSV=/output/pred.csv
AUDIT_CSV=/output/pred_audit.csv

WEB_SEARCH_ENABLED=false
WEB_SEARCH_PROVIDER=duckduckgo
WEB_SEARCH_ENDPOINT=

OLLAMA_HOST_PORT=11435
```

- [ ] **Step 4: Verify `.env.example` test passes**

Run:

```bash
rtk pytest tests/test_docker_config.py::test_env_example_documents_compose_runtime_knobs -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add .env.example tests/test_docker_config.py
rtk git commit -m "docs: add compose env example"
```

## Task 7: Document Run Commands

**Files:**
- Modify: `README.md`
- Test: `tests/test_docker_config.py`

- [ ] **Step 1: Add failing README test**

Append to `tests/test_docker_config.py`:

```python
def test_readme_documents_compose_cpu_gpu_and_outputs():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "docker compose up --build" in readme
    assert "docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build" in readme
    assert "data/public_test.csv" in readme
    assert "output/pred.csv" in readme
    assert "output/pred_audit.csv" in readme
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
rtk pytest tests/test_docker_config.py::test_readme_documents_compose_cpu_gpu_and_outputs -q
```

Expected: FAIL because `README.md` currently only contains the project title.

- [ ] **Step 3: Replace `README.md` content**

Use:

```markdown
# Atlas_Agent

## Run with Docker Compose

Prepare input data:

```bash
mkdir -p data output
ls data/public_test.csv
```

Run CPU stack:

```bash
docker compose up --build
```

Run GPU stack with NVIDIA Container Toolkit:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

The app writes:

- `output/pred.csv`
- `output/pred_audit.csv`

Useful overrides:

```bash
MODEL_NAME=qwen3.5:0.8b BATCH_SIZE=20 OLLAMA_NUM_PREDICT=512 docker compose up --build
```

To use another mounted input file:

```bash
INPUT_CSV=/data/public_test.csv OUTPUT_CSV=/output/pred.csv docker compose up --build
```
```

- [ ] **Step 4: Verify README test passes**

Run:

```bash
rtk pytest tests/test_docker_config.py::test_readme_documents_compose_cpu_gpu_and_outputs -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add README.md tests/test_docker_config.py
rtk git commit -m "docs: document docker compose usage"
```

## Task 8: End-to-End Verification

**Files:**
- No file changes expected unless verification exposes a defect.

- [ ] **Step 1: Run unit tests**

Run:

```bash
rtk pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Validate CPU Compose config**

Run:

```bash
rtk docker compose config
```

Expected: command exits 0 and includes `atlas-agent`, `atlas-ollama`, `./data:/data:ro`, and `./output:/output`.

- [ ] **Step 3: Validate GPU Compose config**

Run:

```bash
rtk docker compose -f docker-compose.yml -f docker-compose.gpu.yml config
```

Expected: command exits 0 and includes NVIDIA device reservations on `ollama`.

- [ ] **Step 4: Run a smoke test when `data/public_test.csv` exists**

Run:

```bash
rtk docker compose up --build --abort-on-container-exit app
```

Expected: `app` exits 0, `output/pred.csv` exists, and `output/pred_audit.csv` exists.

- [ ] **Step 5: Inspect generated outputs**

Run:

```bash
rtk ls -l output/pred.csv output/pred_audit.csv
```

Expected: both files are present and non-empty.

- [ ] **Step 6: Commit any verification fixes**

Only if a verification defect required code changes:

```bash
rtk git add Dockerfile docker-compose.yml docker-compose.gpu.yml entrypoints.sh main.py README.md .env.example tests/test_docker_config.py
rtk git commit -m "fix: complete compose packaging verification"
```

## Self-Review

- Spec coverage: The plan covers Docker image, Compose CPU stack, GPU override, env defaults, mounted input/output, entrypoint behavior, tests, docs, and smoke verification.
- Placeholder scan: No task uses TBD/TODO/fill-in instructions; code snippets and commands are explicit.
- Type consistency: Environment variable names are consistent across `main.py`, `entrypoints.sh`, `docker-compose.yml`, `.env.example`, and README: `INPUT_CSV`, `OUTPUT_CSV`, `AUDIT_CSV`, `MODEL_NAME`, `BATCH_SIZE`, `OLLAMA_NUM_PREDICT`, and web search variables.
