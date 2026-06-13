# Huong dan build va chay Ollama bang Docker Compose tren Windows

Tai lieu nay danh cho may Windows dung Docker Desktop. Neu dang dung Linux/Ubuntu, xem `ollama_run_linux.md`.

Mac dinh project co the chay Ollama bang CPU. Neu may co GPU NVIDIA va Docker Desktop nhan duoc GPU qua WSL2 thi co the chay them file `docker-compose.gpu.yml`.

## 1. Yeu cau truoc khi chay

Can co san tren may Windows:

- Docker Desktop
- WSL2 backend da bat trong Docker Desktop
- Internet de Docker pull image va pull model Ollama
- Terminal PowerShell, Windows Terminal, hoac terminal trong WSL

Neu muon chay bang GPU NVIDIA, can them:

- NVIDIA driver cho Windows co ho tro WSL2/CUDA
- Docker Desktop nhan duoc GPU tu WSL2

Kiem tra Docker Compose:

```powershell
docker compose version
```

Kiem tra GPU NVIDIA trong Docker:

```powershell
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Neu lenh tren in ra bang `nvidia-smi` thi co the dung GPU mode. Neu khong, hay chay CPU mode truoc.

## 2. Chuan bi project

Di vao thu muc goc cua project. Vi du trong PowerShell:

```powershell
cd path\to\Atlas_Agent
```

Hoac trong WSL:

```bash
cd /path/to/Atlas_Agent
```

Dam bao cac file compose va Dockerfile ton tai:

```powershell
dir docker-compose.yml, docker-compose.gpu.yml, Dockerfile, entrypoints.sh
```

Neu chay ca service `app`, can dat du 2 file data vao thu muc `data`:

```powershell
dir data\public_test.csv, data\private_test.csv
```

Neu chi muon chay rieng Ollama thi chua can 2 file CSV nay.

## 3. Build image app

Build image cho service `app`:

```powershell
docker compose build app
```

Lenh nay se cai cac package trong `requirements.txt`, nen co the mat nhieu thoi gian. Neu chi muon start rieng Ollama de pull/chay model thi co the bo qua buoc build app.

## 4. Chay mac dinh bang CPU

Chay rieng Ollama va service pull model:

```powershell
docker compose up -d ollama ollama-pull
```

Lenh tren se:

- Start container `ollama`
- Mo port `11435` tren Windows host va map vao port `11434` trong container
- Luu model vao thu muc `ollama-data`
- Tu dong pull model `qwen3.5:0.8b` bang service `ollama-pull`

Neu muon build va chay toan bo stack gom ca app:

```powershell
docker compose up -d --build
```

## 5. Chay bang GPU NVIDIA

Chi dung muc nay neu may da pass lenh:

```powershell
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Chay rieng Ollama bang GPU va pull model:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d ollama ollama-pull
```

Build va chay toan bo stack bang GPU mode:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

File `docker-compose.gpu.yml` chi override service `ollama` de container co quyen dung GPU. App van ket noi toi Ollama qua `OLLAMA_BASE_URL=http://ollama:11434` trong Docker network.

## 6. Kiem tra sau khi up

Kiem tra container:

```powershell
docker compose ps
```

Neu dang chay GPU mode:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml ps
```

Kiem tra Ollama API tu Windows host:

```powershell
curl http://localhost:11435/api/tags
```

Trong PowerShell cu, neu `curl` bi alias sang `Invoke-WebRequest`, co the dung:

```powershell
curl.exe http://localhost:11435/api/tags
```

Kiem tra model trong container Ollama:

```powershell
docker compose exec ollama ollama list
```

Neu dang chay GPU mode, kiem tra GPU trong container:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml exec ollama nvidia-smi
```

## 7. Xem log

CPU mode:

```powershell
docker compose logs -f ollama
docker compose logs -f ollama-pull
docker compose logs -f app
```

GPU mode:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml logs -f ollama
docker compose -f docker-compose.yml -f docker-compose.gpu.yml logs -f ollama-pull
docker compose -f docker-compose.yml -f docker-compose.gpu.yml logs -f app
```

## 8. Dung stack

Dung CPU mode:

```powershell
docker compose down
```

Dung GPU mode:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml down
```

Cac model Ollama van duoc giu trong thu muc `ollama-data`. Neu muon xoa model/data da pull, hay `down` stack truoc roi xoa thu muc `ollama-data`.

## 9. Loi thuong gap tren Windows

Neu `app` thoat voi loi thieu file CSV, hay them 2 file sau vao thu muc `data`:

```text
data/public_test.csv
data/private_test.csv
```

Neu gap loi port `11434` da duoc dung, project nay da publish Ollama ra host bang port `11435`. Kiem tra API bang:

```powershell
curl.exe http://localhost:11435/api/tags
```

Neu gap loi GPU:

```text
Error response from daemon: could not select device driver "nvidia" with capabilities: [[gpu]]
```

Hay kiem tra lenh GPU test:

```powershell
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Neu lenh test nay cung loi, van de nam o Docker Desktop/WSL2/NVIDIA driver tren Windows, khong phai compose file. Cach xu ly thuong la:

- Cap nhat NVIDIA driver cho Windows
- Dam bao Docker Desktop dang dung WSL2 backend
- Restart Docker Desktop
- Chay CPU mode neu chua can GPU: `docker compose up -d ollama ollama-pull`

Khong chay cac lenh Ubuntu nhu `sudo apt install nvidia-container-toolkit` truc tiep trong PowerShell Windows. Cac lenh do chi dung cho Linux host.

Neu model chua xuat hien trong `ollama list`, xem log service pull model:

```powershell
docker compose logs -f ollama-pull
```

Trong luc model dang duoc pull, API `/api/tags` co the tra ve `{"models":[]}`. Doi den khi `ollama-pull` ket thuc thanh cong roi kiem tra lai.
