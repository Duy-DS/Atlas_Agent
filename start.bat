@echo off
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi >nul 2>&1

if %errorlevel%==0 (
    docker compose -f docker-compose.yml -f docker-compose.gpu.yml up
) else (
    docker compose up
)