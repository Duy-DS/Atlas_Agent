#!/bin/bash

if docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi >/dev/null 2>&1
then
    echo "GPU detected"
    docker compose -f docker-compose.yml -f docker-compose.gpu.yml up
else
    echo "GPU not detected"
    docker compose up
fi