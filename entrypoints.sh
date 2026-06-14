#!/bin/sh
set -e

INPUT_CSV="${INPUT_CSV:-/data/public_test.csv}"
OUTPUT_CSV="${OUTPUT_CSV:-/output/pred.csv}"
AUDIT_CSV="${AUDIT_CSV:-/output/pred_audit.csv}"
APP_MODE="${APP_MODE:-python}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
LLM_BACKEND="${LLM_BACKEND:-ollama}"

printf "%s\n" "Starting Atlas Agent Standalone Stack..."
printf "%s\n" "Input: ${INPUT_CSV}"
printf "%s\n" "Output: ${OUTPUT_CSV}"
printf "%s\n" "Audit: ${AUDIT_CSV}"

if [ ! -f "$INPUT_CSV" ]; then
  printf "%s\n" "ERROR: input CSV not found: $INPUT_CSV"
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_CSV")"
mkdir -p "$(dirname "$AUDIT_CSV")"

if [ "$LLM_BACKEND" = "vllm" ]; then
  printf "%s\n" "Using external vLLM endpoint at ${LLM_BASE_URL:-http://vllm:8000/v1}"
  export INPUT_CSV OUTPUT_CSV AUDIT_CSV
  export LLM_BASE_URL="${LLM_BASE_URL:-http://vllm:8000/v1}"
  export LLM_MODEL_NAME="${LLM_MODEL_NAME:-Qwen/Qwen2.5-7B-Instruct-AWQ}"
  export LLM_API_KEY="${LLM_API_KEY:-EMPTY}"
else
  printf "%s\n" "Starting local Ollama server in background..."
  ollama serve > /var/log/ollama.log 2>&1 &

  if [ "${WAIT_FOR_OLLAMA:-true}" = "true" ]; then
    printf "%s\n" "Waiting for Ollama to be healthy at ${OLLAMA_BASE_URL}..."
    until curl -fsS "${OLLAMA_BASE_URL}/api/tags" >/dev/null 2>&1; do
      sleep 2
    done
    printf "%s\n" "Ollama is ready!"
  fi

  export INPUT_CSV OUTPUT_CSV AUDIT_CSV OLLAMA_BASE_URL
  export LLM_BASE_URL="${OLLAMA_BASE_URL}/v1"
  export LLM_MODEL_NAME="${MODEL_NAME:-qwen3.5:4b}"
fi

if [ "$APP_MODE" = "streamlit" ]; then
  printf "%s\n" "Starting Streamlit..."
  exec streamlit run /app/main.py --server.address=0.0.0.0 --server.port=8501
fi

printf "%s\n" "Running main.py..."
exec python /app/main.py
