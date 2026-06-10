# Toi uu toc do xu ly cau hoi

## Muc tieu

Toi uu toc do khi dung Ollama de tra loi so luong cau hoi lon ma khong can nang phan cung. Thay doi nay huong toi ca model nho hien tai `qwen3.5:0.8b` va model lon hon trong tuong lai, vi cac tham so chinh duoc tach thanh cau hinh.

## Nguyen nhan chay cham truoc khi thay doi

1. `main.py` goi model tung cau mot. Voi 70 cau se co 70 request, voi 2000 cau se thanh 2000 request. Overhead moi lan goi Ollama lam tong thoi gian tang gan tuyen tinh.
2. Prompt cu yeu cau model lap luan theo cac buoc `Nhan Dien`, `Phan Tich`, `Ket Luan`. Cach nay hop de debug nhung rat ton token khi can xuat dap an hang loat.
3. `num_predict` dang de cao, lam model co ngan sach sinh token lon hon nhu cau thuc te.
4. Model reasoning co the sinh thinking thay vi final answer. Neu `content` rong thi chuong trinh de roi ve `N/A`.
5. Khi gui qua nhieu cau mot lan ma khong validate, model co the tra thieu qid hoac dap an ngoai A/B/C/D.

## Da thay doi gi

### 1. Batch nhieu cau trong mot request

`main.py` da doi tu xu ly tung cau sang xu ly theo batch. Mac dinh:

```text
BATCH_SIZE=20
```

Voi 2000 cau, so request ly thuyet giam tu 2000 xuong khoang 100 request, chua tinh retry.

### 2. Retry chi nhung cau bi loi

Sau moi batch, chuong trinh parse output CSV va kiem tra tung `qid`.

Cau nao thieu output hoac co answer khong hop le se duoc retry rieng trong batch loi. Cau da co dap an hop le khong bi goi lai.

### 3. Giu system prompt goc cua du an

Agent mac dinh dung file:

```text
prompts/system_prompt.md
```

Khong dung `system_prompt_fast.md` lam mac dinh. Toi uu toc do hien nam o pipeline batch/retry va cau hinh `num_predict`, tranh thay doi y do prompt goc cua du an.

### 4. Tat thinking cua Ollama

Trong `agents/agent.py`, lenh goi Ollama dung:

```python
think=False
```

Dieu nay tranh truong hop model chi sinh reasoning trong `message.thinking` va de `message.content` rong.

### 5. Giam ngan sach sinh token

`num_predict` duoc doi thanh cau hinh:

```text
OLLAMA_NUM_PREDICT=512
```

Gia tri nay phu hop voi batch mac dinh 20 cau vi output chi can CSV ngan. Khi tang batch hoac dung model lon hon, co the tang gia tri nay ma khong can sua code.

### 6. Tach cau hinh cho model lon hon sau nay

Cac bien moi co the chinh qua environment:

```text
MODEL_NAME=qwen3.5:0.8b
BATCH_SIZE=20
OLLAMA_NUM_PREDICT=512
SYSTEM_PROMPT_PATH=/app/prompts/system_prompt.md
```

Trong Docker Compose, `MODEL_NAME`, `BATCH_SIZE`, `OLLAMA_NUM_PREDICT` da duoc gan default nhung van cho phep override tu `.env` hoac command line.

## Duoc gi sau khi thay doi

1. Giam manh so lan goi model khi xu ly nhieu cau.
2. Giam token output vi model khong con phai viet phan giai thich.
3. Giam nguy co `N/A` do thinking-only response.
4. Ket qua dau ra on dinh hon vi co validate `qid` va `answer`.
5. De thu nghiem model lon hon sau nay: chi can doi `MODEL_NAME`, tang/giam `BATCH_SIZE` va `OLLAMA_NUM_PREDICT`.

## Goi y cau hinh theo kich thuoc model

### Model nho nhu `qwen3.5:0.8b`

```text
BATCH_SIZE=20
OLLAMA_NUM_PREDICT=512
```

Neu model hay tra thieu dong, giam `BATCH_SIZE` xuong 10.

### Model lon hon nhu `qwen3.5:4b`

Model lon thuong cham hon moi token nhung co the giu format tot hon. Nen thu:

```text
BATCH_SIZE=30
OLLAMA_NUM_PREDICT=768
```

Neu chay CPU va qua cham, giam `BATCH_SIZE` ve 10-20.

### Khi can toi uu toc do toi da

```text
BATCH_SIZE=30
OLLAMA_NUM_PREDICT=512
```

Chi nen dung neu model tra du dong va khong bi cat output.

## Cach chay

Local voi conda env:

```bash
conda run -n atlas_agent python main.py
```

Docker Compose co the override cau hinh:

```bash
MODEL_NAME=qwen3.5:0.8b BATCH_SIZE=20 OLLAMA_NUM_PREDICT=512 docker compose up --build
```

File output:

```text
output/pred.csv
```

## Luu y

Tang model len 4B khong dong nghia nhanh hon. Model lon thuong cham hon tren cung phan cung. Loi ich cua model lon la kha nang giu format va tra loi dung co the tot hon. Vi vay thay doi nay uu tien toi uu pipeline truoc, de khi doi model sau nay chi can chinh cau hinh thay vi sua code.
