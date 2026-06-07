import sys
import io

# Cấu hình encoding UTF-8 cho Windows console để tránh UnicodeEncodeError
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


import os
import hashlib
import math
import torch
from pathlib import Path


# Import các module từ hệ sinh thái Langchain
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_core.tools import tool

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

# Khởi động dotenv để đọc file .env
from dotenv import load_dotenv
load_dotenv()

# Tự động chọn thiết bị (ưu tiên GPU nếu có)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[*] [RAG Engine] Khoi tao thiet bi: {device.upper()}")

# Lựa chọn Embedding: Online (HF Inference API) hoặc Local siêu nhẹ (all-MiniLM-L6-v2)
hf_token = os.getenv("HF_TOKEN")
if hf_token:
    print("[*] Dang su dung online HuggingFace Inference API de sinh embedding (Khong tai file weight)...")
    try:
        from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
        embeddings = HuggingFaceInferenceAPIEmbeddings(
            api_key=hf_token,
            model_name="BAAI/bge-m3"
        )
    except Exception as e:
        print(f"[!] Loi khi goi HuggingFace Inference API ({e}). Chuyen sang fallback.")
        embeddings = _FallbackEmbeddings()
else:
    print("[!] Khong tim thay HF_TOKEN trong file .env.")
    print("[*] Dang su dung local embedding sieu nhe 'all-MiniLM-L6-v2' (chi ~80MB, tai ve trong vai giay)...")
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': device}
        )
    except Exception as error:
        print(f"[!] Khong khoi dong duoc all-MiniLM-L6-v2 ({error}). Dung fallback TF-IDF local.")
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
        print(f"[!] Loi: Khong tim thay file {file_path}")
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
    
    print(f"[*] Da chia tai lieu thanh {len(chunks)} chunks. Tien hanh nhung vao ChromaDB...")

    # 3. Lưu vào Vector DB (Tự động tính toán vector và lưu xuống ổ cứng)
    vectorstore.add_documents(chunks)
    print("[+] Hoan tat nap du lieu!")

# =====================================================================
# BƯỚC 3: TOOL TRA CỨU CƠ BẢN (KHÔNG RERANK)
# =====================================================================

@tool
def search_rag_database(query: str) -> str:
    """
    Công cụ tìm kiếm thông tin chuyên sâu từ cơ sở dữ liệu tri thức (RAG).
    Main Agent CẦN gọi công cụ này khi gặp các câu hỏi cần bối cảnh thực tế, 
    thông tin chuyên môn, hoặc dữ liệu đặc thù không có sẵn trong bộ nhớ.
    
    Args:
        query (str): Câu hỏi hoặc từ khóa cần tra cứu.
        
    Returns:
        str: Chuỗi văn bản chứa Top 3 đoạn thông tin liên quan nhất, 
             được phân cách bởi dấu gạch ngang để dễ dàng tổng hợp.
    """
    # NHIỆM VỤ 1: Tìm ra 3 đoạn chunk input từ RAG Engine
    # (Giả định 'vectorstore' đã được khởi tạo thành công ở Bước 1)
    docs = vectorstore.similarity_search(query, k=3)
    
    if not docs:
        return "Không tìm thấy thông tin nào liên quan trong cơ sở dữ liệu."

    # NHIỆM VỤ 2: Xử lý 3 chunks rời rạc thành 1 output là chuỗi ký tự
    top_chunks_text = [doc.page_content for doc in docs]
    context_str = "\n\n---\n\n".join(top_chunks_text)
    
    return f"THÔNG TIN TRA CỨU ĐƯỢC TỪ RAG:\n{context_str}"



