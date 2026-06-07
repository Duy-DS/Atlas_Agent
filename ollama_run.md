# Huong dan build va chay Ollama bang Docker Compose

Tai lieu nay danh cho nguoi vua nhan source code cua project va muon build, start he thong len bang Docker Compose.

Mac dinh project chay Ollama bang CPU. Neu may co GPU NVIDIA va da cai NVIDIA Container Toolkit thi co the chay them file `docker-compose.gpu.yml`.

## 1. Yeu cau truoc khi chay

Can co san tren may:

- Docker
- Docker Compose V2 (`docker compose version`)
- Internet de Docker pull image va pull model Ollama

Neu muon chay bang GPU NVIDIA, can them:

- NVIDIA driver
- NVIDIA Container Toolkit

Kiem tra Docker Compose:

```bash
docker compose version
```

Kiem tra GPU NVIDIA neu can chay GPU:

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Neu lenh `nvidia-smi` trong Docker chay duoc thi co the dung GPU mode.

## 2. Chuan bi project

Di vao thu muc goc cua project:

```bash
cd Atlas_Agent
```

Dam bao cac file compose va Dockerfile ton tai:

```bash
ls docker-compose.yml docker-compose.gpu.yml Dockerfile entrypoints.sh
```

Neu chay ca service `app`, can dat du 2 file data vao thu muc `data`:

```bash
ls data/public_test.csv data/private_test.csv
```

Neu chi muon chay rieng Ollama thi chua can 2 file CSV nay.

## 3. Build image app

Build image cho service `app`:

```bash
docker compose build app
```

Lenh nay se cai cac package trong `requirements.txt`, nen co the mat nhieu thoi gian. Neu chi muon start rieng Ollama de pull/chay model thi co the bo qua buoc build app.

## 4. Chay mac dinh bang CPU

Chay rieng Ollama va service pull model:

```bash
docker compose up -d ollama ollama-pull
```

Lenh tren se:

- Start container `ollama`
- Mo port `11434` ra host
- Luu model vao thu muc `ollama-data`
- Tu dong pull model `qwen3.5:0.8b` bang service `ollama-pull`

Neu muon build va chay toan bo stack gom ca app:

```bash
docker compose up -d --build
```

## 5. Chay bang GPU NVIDIA

Chi dung muc nay neu may host da pass lenh kiem tra `docker run --rm --gpus all ... nvidia-smi`.

Chay rieng Ollama bang GPU va pull model:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d ollama ollama-pull
```

Build va chay toan bo stack bang GPU mode:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

File `docker-compose.gpu.yml` chi override service `ollama` de container co quyen dung GPU. App van ket noi toi Ollama qua `OLLAMA_BASE_URL=http://ollama:11434`.

## 6. Kiem tra sau khi up

Kiem tra container:

```bash
docker compose ps
```

Neu dang chay GPU mode:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml ps
```

Kiem tra Ollama API tu may host:

```bash
curl http://localhost:11434/api/tags
```

Kiem tra model trong container Ollama:

```bash
docker compose exec ollama ollama list
```

Neu dang chay GPU mode, kiem tra GPU trong container:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml exec ollama nvidia-smi
```

## 7. Xem log

CPU mode:

```bash
docker compose logs -f ollama
docker compose logs -f ollama-pull
docker compose logs -f app
```

GPU mode:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml logs -f ollama
docker compose -f docker-compose.yml -f docker-compose.gpu.yml logs -f ollama-pull
docker compose -f docker-compose.yml -f docker-compose.gpu.yml logs -f app
```

## 8. Dung stack

Dung CPU mode:

```bash
docker compose down
```

Dung GPU mode:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml down
```

Cac model Ollama van duoc giu trong thu muc `ollama-data`. Neu muon xoa model/data da pull, hay `down` stack truoc roi xoa thu muc `ollama-data`.

## 9. Loi thuong gap

Neu `app` thoat voi loi thieu file CSV, hay them 2 file sau vao thu muc `data`:

```bash
data/public_test.csv
data/private_test.csv
```

Neu GPU mode bao loi khong tim thay GPU, hay kiem tra lai NVIDIA driver va NVIDIA Container Toolkit tren may host.

Neu model chua xuat hien trong `ollama list`, xem log service pull model:

```bash
docker compose logs -f ollama-pull
```
