# Docker Compose Usage

This guide explains how to run Atlas Agent with Docker Compose. The stack contains three services:

- `ollama`: serves the local model API on the Compose network.
- `ollama-pull`: waits for Ollama and pulls `MODEL_NAME` before the app starts.
- `app`: runs `python /app/main.py`, reads CSV input from `/data`, and writes result files to `/output`.

## Prerequisites

Install these on the host machine:

- Docker Engine
- Docker Compose v2
- NVIDIA Container Toolkit, only when using GPU mode

Check Docker Compose:

```bash
docker compose version
```

## Input and Output Layout

Create the runtime folders from the repository root:

```bash
mkdir -p data output ollama-data chroma-data
```

Place the input file here:

```text
data/public_test.csv
```

The app writes these files:

```text
output/pred.csv
output/pred_audit.csv
```

`pred.csv` contains the submission-style `qid,answer` output. `pred_audit.csv` contains extra audit columns for confidence/search behavior so you can inspect why an answer was produced.

## Environment Configuration

Copy the example file if you want local overrides:

```bash
cp .env.example .env
```

Default values:

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

Important notes:

- `INPUT_CSV`, `OUTPUT_CSV`, and `AUDIT_CSV` are container paths, not host paths.
- Because Compose mounts `./data:/data:ro`, host file `data/public_test.csv` appears inside the container as `/data/public_test.csv`.
- Because Compose mounts `./output:/output`, container output `/output/pred.csv` appears on the host as `output/pred.csv`.
- `OLLAMA_HOST_PORT=11435` exposes Ollama on `http://localhost:11435` from the host. Inside Compose, the app uses `http://ollama:11434`.

## CPU Run

From the repository root:

```bash
docker compose up --build
```

To force a fresh run after changing code or dependencies:

```bash
docker compose build --no-cache app
docker compose up
```

To stop services:

```bash
docker compose down
```

## GPU Run

GPU mode uses the base Compose file plus `docker-compose.gpu.yml`:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

The GPU override only changes the `ollama` service. The app still connects to Ollama through `OLLAMA_BASE_URL=http://ollama:11434`.

If GPU is not detected, verify the NVIDIA runtime on the host:

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

## Running With Different Inputs

If the host file is `data/private_test.csv`, run:

```bash
INPUT_CSV=/data/private_test.csv OUTPUT_CSV=/output/private_pred.csv AUDIT_CSV=/output/private_pred_audit.csv docker compose up --build
```

The file must still live under `data/` because that is the mounted input directory.

## Model and Speed Tuning

Use smaller batches for CPU or weak models:

```bash
BATCH_SIZE=10 docker compose up --build
```

Use a different Ollama model:

```bash
MODEL_NAME=qwen3.5:0.8b docker compose up --build
```

If output is truncated, increase prediction length:

```bash
OLLAMA_NUM_PREDICT=768 docker compose up --build
```

## Web Search

Web search is disabled by default in Compose:

```dotenv
WEB_SEARCH_ENABLED=false
```

Enable DuckDuckGo-backed search:

```bash
WEB_SEARCH_ENABLED=true WEB_SEARCH_PROVIDER=duckduckgo docker compose up --build
```

Use a custom HTTP search service:

```bash
WEB_SEARCH_ENABLED=true WEB_SEARCH_ENDPOINT=http://your-search-service/search docker compose up --build
```

## Verification

Validate Compose syntax without starting containers:

```bash
docker compose config
```

Validate GPU Compose syntax:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml config
```

After a run, inspect generated files:

```bash
ls -l output/pred.csv output/pred_audit.csv
```

## Troubleshooting

If the app exits with `input CSV not found`, confirm the host file exists:

```bash
ls data/public_test.csv
```

If the app waits on Ollama for a long time, check Ollama logs:

```bash
docker compose logs -f ollama
```

If model pulling fails, rerun only the pull service after Ollama is healthy:

```bash
docker compose up ollama-pull
```

If you want to remove containers while keeping downloaded models and outputs:

```bash
docker compose down
```

If you want to remove downloaded Ollama models too, delete `ollama-data/` manually after stopping containers.
