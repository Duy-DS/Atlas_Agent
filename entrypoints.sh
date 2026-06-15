#!/bin/sh
set -e

INPUT_CSV="${INPUT_CSV:-/data/public_test.csv, /data/private_test.csv}"

OUTPUT_CSV="${OUTPUT_CSV:-/output/pred.csv}"
APP_MODE="${APP_MODE:-python}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://ollama:11434}"

printf "%s\n" "Starting Atlas Agent..."
printf "%s\n" "Input: ${INPUT_CSV}"
printf "%s\n" "Output: ${OUTPUT_CSV}"

if [ ! -f "$INPUT_CSV" ]; then
  printf "%s\n" "ERROR: input CSV not found: $INPUT_CSV"
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_CSV")"


if [ "${WAIT_FOR_OLLAMA:-true}" = "true" ]; then
  printf "%s\n" "Waiting for Ollama at ${OLLAMA_BASE_URL}..."
  until curl -fsS "${OLLAMA_BASE_URL}/api/tags" >/dev/null; do
    sleep 2
  done
fi

export INPUT_CSV OUTPUT_CSV AUDIT_CSV OLLAMA_BASE_URL

if [ "$APP_MODE" = "streamlit" ]; then
  printf "%s\n" "Starting Streamlit..."
  exec streamlit run /app/main.py --server.address=0.0.0.0 --server.port=8501
fi

printf "%s\n" "Running main.py..."
exec python /app/main.py
