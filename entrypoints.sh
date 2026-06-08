#!/bin/sh
set -e

echo "Starting app inside Docker container..."

if [ "$APP_MODE" = "streamlit" ]; then
  STREAMLIT_SCRIPT="${STREAMLIT_SCRIPT:-/app/streamlit_chat.py}"
  echo "Starting Streamlit: $STREAMLIT_SCRIPT"
  streamlit run "$STREAMLIT_SCRIPT" \
    --server.address=0.0.0.0 \
    --server.port=8501
else
  echo "Checking data files..."

  if [ ! -f "/data/public_test.csv" ]; then
    echo "ERROR: /data/public_test.csv not found"
    exit 1
  fi

  if [ ! -f "/data/private_test.csv" ]; then
    echo "ERROR: /data/private_test.csv not found"
    exit 1
  fi

  echo "Data files found."
  echo "Running main.py..."
  python /app/main.py
fi
