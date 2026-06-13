# Atlas_Agent

Atlas Agent runs a CSV question-answering pipeline with Ollama. The Docker Compose stack starts Ollama, pulls the configured model, runs the app, and writes predictions to `output/`.

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

See `docs/docker_compose_usage.md` for detailed setup, GPU notes, environment variables, and troubleshooting.
