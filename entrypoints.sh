#!/bin/sh
set -e

#!/bin/sh
set -e

# Auto-detect CSV input file if not specified
if [ -z "$INPUT_CSV" ]; then
    # Look for public_test or private_test CSV files
    for file in /app/data/public_test*.csv /app/data/private_test*.csv; do
        if [ -f "$file" ]; then
            INPUT_CSV="$file"
            break
        fi
    done
    
    # Fallback to any CSV in data folder
    if [ -z "$INPUT_CSV" ]; then
        for file in /app/data/*.csv; do
            if [ -f "$file" ]; then
                INPUT_CSV="$file"
                break
            fi
        done
    fi
    
    # Final fallback
    INPUT_CSV="${INPUT_CSV:-/app/data/public_test.csv}"
fi

OUTPUT_CSV="${OUTPUT_CSV:-/app/output/pred.csv}"
APP_MODE="${APP_MODE:-python}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://ollama:11434}"
MODEL_NAME="${MODEL_NAME:-qwen3.5:4b}"

printf "%s\n" "Starting Atlas Agent..."
printf "%s\n" "Input: ${INPUT_CSV}"
printf "%s\n" "Output: ${OUTPUT_CSV}"
printf "%s\n" "Model: ${MODEL_NAME}"
printf "%s\n" "Input format: CSV"

if [ ! -f "$INPUT_CSV" ]; then
  printf "%s\n" "ERROR: input CSV file not found: $INPUT_CSV"
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_CSV")"

if [ "${WAIT_FOR_OLLAMA:-true}" = "true" ]; then
  printf "%s\n" "Waiting for Ollama at ${OLLAMA_BASE_URL}..."
  until curl -fsS "${OLLAMA_BASE_URL}/api/tags" >/dev/null; do
    sleep 2
  done
  
  printf "%s\n" "Verifying model ${MODEL_NAME} is available..."
  until curl -fsS "${OLLAMA_BASE_URL}/api/tags" | grep -q "\"name\":\"${MODEL_NAME}\""; do
    printf "%s\n" "Model ${MODEL_NAME} not ready, waiting..."
    sleep 5
  done
  printf "%s\n" "Model ${MODEL_NAME} is ready!"
fi

export INPUT_CSV OUTPUT_CSV AUDIT_CSV OLLAMA_BASE_URL

if [ "$APP_MODE" = "streamlit" ]; then
  printf "%s\n" "Starting Streamlit..."
  exec streamlit run /app/main.py --server.address=0.0.0.0 --server.port=8501
fi

printf "%s\n" "Running main.py..."
python /app/main.py
exit_code=$?
printf "%s\n" "Atlas Agent finished with exit code: $exit_code"
exit $exit_code
