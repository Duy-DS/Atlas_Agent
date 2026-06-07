import os
import hashlib
import math
import torch
from pathlib import Path

# Import các module từ hệ sinh thái Langchain
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma


class _FallbackEmbeddings:
    def __init__(self, dimension: int = 1024):
        self.dimension = dimension

    def _encode_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in text.lower().split():
            index = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self.dimension
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._encode_text(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._encode_text(text)

# =====================================================================
# BƯỚC 1: KHỞI TẠO ĐƯỜNG DẪN & MÔ HÌNH EMBEDDING
# =====================================================================

# Cấu hình đường dẫn đa nền tảng (Windows/Linux)
BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_PATH = BASE_DIR / "chroma_db"

# Tự động chọn thiết bị (ưu tiên GPU nếu có)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[*] Đang khởi tạo RAG Engine trên thiết bị: {device.upper()}")

# Khởi tạo Embedding Model BGE-m3 thông qua Langchain
print("[*] Đang tải mô hình BGE-m3 via Langchain...")
try:
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3",
        model_kwargs={'device': device},
        encode_kwargs={'normalize_embeddings': True} # Khuyến nghị bật chuẩn hóa cho BGE-m3
    )
except Exception as error:
    print(f"[!] Không tải được BGE-m3 via Langchain ({error}). Dùng fallback embedding local.")
    embeddings = _FallbackEmbeddings()

# Khởi tạo Vector Database
vectorstore = Chroma(
    collection_name="knowledge_base_collection",
    embedding_function=embeddings,
    persist_directory=str(CHROMA_PATH)
)

# =====================================================================
# BƯỚC 2: XÂY DỰNG INGESTION PIPELINE BẰNG LANGCHAIN
# =====================================================================

def ingest_document(file_path: str):
    """
    Sử dụng Document Loader và Text Splitter của Langchain để nạp dữ liệu.
    """
    path = Path(file_path)
    if not path.exists():
        print(f"[!] Lỗi: Không tìm thấy file {file_path}")
        return

    # 1. Đọc file
    loader = TextLoader(str(path), encoding="utf-8")
    documents = loader.load()

    # 2. Cắt văn bản thông minh (ưu tiên giữ nguyên câu/đoạn)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=100,
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    
    print(f"[*] Đã chia tài liệu thành {len(chunks)} chunks. Tiến hành nhúng vào ChromaDB...")

    # 3. Lưu vào Vector DB (Tự động tính toán vector và lưu xuống ổ cứng)
    vectorstore.add_documents(chunks)
    print("[+] Hoàn tất nạp dữ liệu!")

# =====================================================================
# BƯỚC 3: TOOL TRA CỨU CƠ BẢN (KHÔNG RERANK)
# =====================================================================

def search_rag_database(query: str) -> str:
    """
    Tool tìm kiếm cung cấp cho LangGraph Agent.
    Thực hiện Similarity Search đơn thuần (Top 3).
    """
    # Lấy top 3 chunks có độ tương đồng vector cao nhất
    docs = vectorstore.similarity_search(query, k=1)
    
    if not docs:
        return "Không tìm thấy thông tin nào liên quan trong cơ sở dữ liệu."

    # Rút trích nội dung (page_content) từ các chunks
    top_chunks_text = [doc.page_content for doc in docs]
    
    # Gộp thành 1 chuỗi hoàn chỉnh
    context_str = "\n\n---\n\n".join(top_chunks_text)
    return f"THÔNG TIN TRA CỨU ĐƯỢC:\n{context_str}"

# =====================================================================
# BƯỚC 4: KIỂM THỬ ĐỘC LẬP (UNIT TEST)
# =====================================================================

if __name__ == "__main__":
    print("\n--- BẮT ĐẦU UNIT TEST LANGCHAIN RAG ---")
    
    # 1. Tạo mock data sạch sẽ (không lặp từ)
    mock_file = BASE_DIR / "data" / "mock_knowledge.txt"
    mock_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(mock_file, "w", encoding="utf-8") as f:
        f.write(
            "Thông tin cuộc thi HackAIthon 2026: Cuộc thi có 3 bảng đấu. "
            "Đối với Bảng C (Innovator), các đội sẽ xây dựng AI Agent có khả năng tự luận logic. "
            "Cơ cấu giải thưởng của Bảng C vô cùng hấp dẫn. Giải thưởng Bảng C HackAIthon gồm 20 triệu VNĐ cho đội xuất sắc đạt giải Nhất. "
            "Giải Nhì nhận được 15 triệu VNĐ và Giải Ba là 10 triệu VNĐ."
        )
            
    # 2. Nạp dữ liệu
    print("\n>> Đang test nạp dữ liệu...")
    ingest_document(str(mock_file))
    
    # 3. Test Tool tìm kiếm
    print("\n>> Đang test chức năng Search...")
    test_query = "Giải thưởng cho đội đạt giải Nhất bảng C là bao nhiêu?"
    result = search_rag_database(test_query)
    
    print(f"\n[CÂU HỎI]: {test_query}")
    print(f"[KẾT QUẢ TỪ RAG]:\n{result}")
    print("\n--- UNIT TEST HOÀN TẤT ---")