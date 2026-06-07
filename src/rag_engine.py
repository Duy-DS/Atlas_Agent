import os
import hashlib
import math
from pathlib import Path
import torch
import chromadb

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(*tool_args, **tool_kwargs):
        if tool_args and callable(tool_args[0]) and not tool_kwargs:
            return tool_args[0]

        def decorator(function):
            return function

        return decorator

try:
    from sentence_transformers import SentenceTransformer
except Exception as import_error:
    SentenceTransformer = None
    _sentence_transformers_import_error = import_error

try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
except Exception as import_error:
    AutoModelForSequenceClassification = None
    AutoTokenizer = None
    _transformers_import_error = import_error


class _FallbackEmbeddingModel:
    def __init__(self, dimension=1024):
        self.dimension = dimension

    def encode(self, texts, show_progress_bar=False):
        if isinstance(texts, str):
            texts = [texts]

        embeddings = []
        for text in texts:
            vector = [0.0] * self.dimension
            tokens = text.lower().split()

            for token in tokens:
                index = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self.dimension
                vector[index] += 1.0

            norm = math.sqrt(sum(value * value for value in vector))
            if norm:
                vector = [value / norm for value in vector]

            embeddings.append(vector)

        return embeddings


def _fallback_rerank_scores(query, chunks):
    query_tokens = set(query.lower().split())
    if not query_tokens:
        return [0.0 for _ in chunks]

    scores = []
    for chunk in chunks:
        chunk_tokens = set(chunk.lower().split())
        overlap = len(query_tokens & chunk_tokens)
        scores.append(overlap / len(query_tokens))
    return scores

# =====================================================================
# BƯỚC 1: KHỞI TẠO ĐƯỜNG DẪN & CẤU HÌNH VECTOR DATABASE
# =====================================================================

# Sử dụng pathlib để đảm bảo hệ thống tự nhận diện đúng đường dẫn trên cả Windows (Dev 3) và Linux (Docker)[cite: 80].
BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_PATH = BASE_DIR / "chroma_db"

# Khởi tạo ChromaDB ở chế độ Persistent (Lưu thẳng xuống ổ cứng cục bộ)[cite: 93, 119, 136, 325].
# Tuyệt đối không dùng Cloud DB[cite: 34, 118].
chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
collection = chroma_client.get_or_create_collection(name="knowledge_base_collection")

# =====================================================================
# KHỞI TẠO MÔ HÌNH (EMBEDDING & RERANKING)
# =====================================================================

# Kiểm tra môi trường để tự động chuyển đổi giữa GPU và CPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[*] Đang chạy RAG Engine trên thiết bị: {device.upper()}")

# Tải mô hình Embedding BGE-m3 đa ngôn ngữ [cite: 44, 120, 137, 146]
print("[*] Đang tải mô hình BGE-m3...")
try:
    if SentenceTransformer is None:
        raise RuntimeError(f"sentence_transformers import failed: {_sentence_transformers_import_error}")
    embedding_model = SentenceTransformer("BAAI/bge-m3", device=device)
except Exception as error:
    print(f"[!] Không tải được BGE-m3 ({error}). Dùng fallback embedding local.")
    embedding_model = _FallbackEmbeddingModel()

# Tải mô hình Qwen-Rerank (Cross-Encoder) [cite: 47, 96, 138, 147]
print("[*] Đang tải mô hình Qwen-Rerank...")
rerank_tokenizer = None
rerank_model = None
try:
    if AutoTokenizer is None or AutoModelForSequenceClassification is None:
        raise RuntimeError(f"transformers import failed: {_transformers_import_error}")
    rerank_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen-Rerank") # Cập nhật đúng tên model path nếu cần
    rerank_model = AutoModelForSequenceClassification.from_pretrained("Qwen/Qwen-Rerank").to(device)
    rerank_model.eval()
except Exception as error:
    print(f"[!] Không tải được Qwen-Rerank ({error}). Dùng fallback reranker local.")

# =====================================================================
# BƯỚC 2: XÂY DỰNG INGESTION PIPELINE (NẠP & NHÚNG DỮ LIỆU)
# =====================================================================

def chunk_text(text, chunk_size=500, overlap=50):
    """
    Chia nhỏ văn bản thành các đoạn (khoảng 500 từ, gối nhau 50 từ)[cite: 88, 103].
    """
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def ingest_document(file_path: str):
    """
    Đọc file tài liệu (.txt), chia nhỏ, nhúng vector bằng BGE-m3 và lưu vào ChromaDB[cite: 154, 326].
    """
    path = Path(file_path)
    if not path.exists():
        print(f"[!] Lỗi: Không tìm thấy file {file_path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_text(text)
    print(f"[*] Đã chia tài liệu thành {len(chunks)} chunks. Tiến hành nhúng...")

    # Chuyển đổi văn bản thành vector 
    embeddings = embedding_model.encode(chunks, show_progress_bar=True)
    if hasattr(embeddings, "tolist"):
        embeddings = embeddings.tolist()

    # Tạo ID cho từng chunk và lưu trữ [cite: 154]
    ids = [f"{path.stem}_chunk_{i}" for i in range(len(chunks))]
    
    collection.upsert(
        documents=chunks,
        embeddings=embeddings,
        ids=ids
    )
    print("[+] Hoàn tất nạp dữ liệu vào ChromaDB!")

# =====================================================================
# BƯỚC 3: THIẾT KẾ TOOL TRA CỨU ĐA TẦNG (CUNG CẤP CHO DEV 2)
# =====================================================================

@tool("search_rag_database")
def search_rag_database(query: str) -> str:
    """
    Tìm kiếm Top 3 ngữ cảnh liên quan nhất trong ChromaDB để phục vụ cho Main Agent của LangGraph.

    Tool này nhận một câu hỏi tự nhiên bằng tiếng Việt từ Dev 2/Main Agent, sau đó thực hiện
    truy hồi đa tầng trên vector database nội bộ:
    1. Mã hoá câu hỏi thành embedding.
    2. Truy vấn ChromaDB để lấy ra các đoạn văn bản ứng viên liên quan nhất.
    3. Rerank các ứng viên bằng mô hình reranker chuyên dụng nếu có sẵn.
    4. Trả về đúng 3 đoạn ngữ cảnh có mức liên quan cao nhất, đã được nối thành một chuỗi.

    Tool này nên được gọi khi Agent cần:
    - Tra cứu thông tin trong kho tri thức nội bộ.
    - Tìm bằng chứng, dữ kiện, hoặc đoạn văn bản gốc liên quan trực tiếp đến câu hỏi.
    - Lấy ngữ cảnh nền trước khi tạo câu trả lời cuối cùng.

    Args:
        query: Câu hỏi hoặc yêu cầu truy vấn của Agent bằng ngôn ngữ tự nhiên. Nên là một câu
            hỏi ngắn gọn nhưng đủ ngữ cảnh, ví dụ: "Giải thưởng cho đội đạt giải Nhất bảng C là bao nhiêu?".

    Returns:
        Một chuỗi văn bản chứa tối đa 3 đoạn ngữ cảnh phù hợp nhất, được ngăn cách bằng dòng '---'.
        Nếu không tìm thấy dữ liệu liên quan, trả về thông báo tiếng Việt tương ứng.
    """
    # --- LỚP 1: EMBEDDING RETRIEVAL ---
    # Truy vấn vector để bốc bộ lọc thô (Top 10 chunks) [cite: 47, 94, 138]
    query_embedding = embedding_model.encode([query])
    if hasattr(query_embedding, "tolist"):
        query_embedding = query_embedding.tolist()
    
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=10 
    )
    
    top_10_chunks = results['documents'][0]
    
    if not top_10_chunks:
        return "Không tìm thấy thông tin nào liên quan trong cơ sở dữ liệu."

    # --- LỚP 2: RERANKING VỚI QWEN ---
    # Đưa các đoạn văn bản qua Qwen-Rerank để chấm điểm liên quan (Cross-Encoder) [cite: 47, 96, 138, 327]
    if rerank_tokenizer is not None and rerank_model is not None:
        pairs = [[query, chunk] for chunk in top_10_chunks]
        
        with torch.no_grad():
            inputs = rerank_tokenizer(pairs, padding=True, truncation=True, return_tensors='pt', max_length=512).to(device)
            scores = rerank_model(**inputs).logits.squeeze(-1).float().cpu().numpy()
    else:
        scores = _fallback_rerank_scores(query, top_10_chunks)
    
    # Kết hợp điểm số với các chunk và sắp xếp giảm dần
    ranked_chunks = sorted(zip(top_10_chunks, scores), key=lambda x: x[1], reverse=True)
    
    # Lọc ra Top 3 chunks chuẩn xác nhất [cite: 47, 96, 138, 303, 327]
    top_3_chunks = [chunk for chunk, score in ranked_chunks[:3]]
    
    # Gộp thành 1 chuỗi hoàn chỉnh để trả về cho Main Agent
    context_str = "\n\n---\n\n".join(top_3_chunks)
    return f"THÔNG TIN TRA CỨU ĐƯỢC:\n{context_str}"


# Ví dụ Dev 2 tích hợp tool này vào Main Agent:
# from src.rag_engine import search_rag_database
# llm_with_tools = llm.bind_tools([search_rag_database])
# response = llm_with_tools.invoke("Giải thưởng cho đội đạt giải Nhất bảng C là bao nhiêu?")

# =====================================================================
# BƯỚC 4: KIỂM THỬ ĐỘC LẬP (UNIT TEST)
# =====================================================================

if __name__ == "__main__":
    # Test độc lập module qua command line 
    print("\n--- BẮT ĐẦU UNIT TEST ---")
    
    # 1. Giả lập tạo một file .txt làm dữ liệu nguồn (mock data)
    mock_file = BASE_DIR / "data" / "mock_knowledge.txt"
    mock_file.parent.mkdir(parents=True, exist_ok=True)
    
    if not mock_file.exists():
        with open(mock_file, "w", encoding="utf-8") as f:
            f.write(
                "Thông tin cuộc thi HackAIthon 2026: Cuộc thi có 3 bảng đấu. "
                "Đối với Bảng C (Innovator), các đội sẽ xây dựng AI Agent có khả năng tự luận logic. "
                "Cơ cấu giải thưởng của Bảng C vô cùng hấp dẫn. Giải thưởng Bảng C HackAIthon gồm 20 triệu VNĐ cho đội xuất sắc đạt giải Nhất. "
                "Giải Nhì nhận được 15 triệu VNĐ và Giải Ba là 10 triệu VNĐ."
            )
            
    # 2. Test nạp dữ liệu
    print(">> Đang test nạp dữ liệu...")
    ingest_document(str(mock_file))
    
    # 3. Test Tool tìm kiếm
    print("\n>> Đang test chức năng Search (Tool Calling)...")
    test_query = "Giải thưởng cho đội đạt giải Nhất bảng C là bao nhiêu?"
    result = search_rag_database(test_query)
    
    print(f"\n[CÂU HỎI]: {test_query}")
    print(f"[KẾT QUẢ TỪ RAG]:\n{result}")
    print("\n--- UNIT TEST HOÀN TẤT ---")