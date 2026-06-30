import os
import subprocess
import sys
from pathlib import Path

# Install markdown library if not installed
try:
    import markdown
except ImportError:
    print("Installing markdown python library...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"])
    import markdown

# Paths
BASE_DIR = Path(__file__).resolve().parents[1]
MD_PATH = BASE_DIR / "docs" / "Atlas_Agent_Methodology_Report.md"
HTML_PATH = BASE_DIR / "docs" / "Atlas_Agent_Methodology_Report.html"
PDF_PATH = BASE_DIR / "docs" / "Atlas_Agent_Methodology_Report.pdf"

# HTML Template with beautiful CSS
CSS_STYLE = """
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: #333333;
    max-width: 800px;
    margin: 40px auto;
    padding: 0 20px;
}
h1 {
    color: #1a365d;
    font-size: 2.2em;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 10px;
    margin-top: 40px;
}
h2 {
    color: #2b6cb0;
    font-size: 1.6em;
    margin-top: 30px;
    border-bottom: 1px solid #edf2f7;
    padding-bottom: 5px;
}
h3 {
    color: #2d3748;
    font-size: 1.25em;
}
code {
    background-color: #f7fafc;
    color: #c53030;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.9em;
}
pre {
    background-color: #f7fafc;
    border: 1px solid #e2e8f0;
    padding: 15px;
    border-radius: 6px;
    overflow-x: auto;
}
pre code {
    background-color: transparent;
    color: #2d3748;
    padding: 0;
}
ul, ol {
    padding-left: 20px;
}
li {
    margin-bottom: 8px;
}
blockquote {
    border-left: 4px solid #3182ce;
    padding: 10px 20px;
    margin: 20px 0;
    background-color: #ebf8ff;
    color: #2b6cb0;
}
/* Flowchart Styles */
.flowchart {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: 30px 0;
}
.flow-step {
    background: #ffffff;
    border: 2px solid #3182ce;
    border-radius: 8px;
    padding: 15px 25px;
    width: 80%;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    text-align: center;
    position: relative;
}
.flow-step h4 {
    margin: 0 0 5px 0;
    color: #1a365d;
    font-size: 1.1em;
}
.flow-step p {
    margin: 0;
    font-size: 0.9em;
    color: #4a5568;
}
.flow-arrow {
    font-size: 24px;
    color: #3182ce;
    margin: 8px 0;
}
.flow-decision {
    background: #fffaf0;
    border: 2px solid #dd6b20;
    border-radius: 8px;
    padding: 15px 25px;
    width: 80%;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    text-align: center;
}
.flow-decision h4 {
    margin: 0 0 5px 0;
    color: #dd6b20;
    font-size: 1.1em;
}
.flow-decision p {
    margin: 0;
    font-size: 0.9em;
    color: #4a5568;
}
"""

def generate_pdf():
    # Read Markdown
    md_content = MD_PATH.read_text(encoding="utf-8")
    
    # Replace Mermaid block with custom HTML Flowchart
    flowchart_html = """
    <div class="flowchart">
        <div class="flow-step">
            <h4>1. Bắt đầu: Tải danh sách câu hỏi</h4>
            <p>Hỗ trợ cả file CSV và JSON định dạng mảng</p>
        </div>
        <div class="flow-arrow">↓</div>
        <div class="flow-step">
            <h4>2. Định tuyến môn học siêu tốc (Rule-Based Router - 0ms)</h4>
            <p>Phân loại nhanh bằng từ khóa chuyên ngành (Toán, Lý, Logic...) để chọn prompt phù hợp</p>
        </div>
        <div class="flow-arrow">↓</div>
        <div class="flow-step">
            <h4>3. Dự đoán hàng loạt (Batch Inference - Cực nhanh)</h4>
            <p>Giới hạn tối đa 128 tokens để tối ưu hóa thời gian chạy và triệt tiêu lỗi lặp từ</p>
        </div>
        <div class="flow-arrow">↓</div>
        <div class="flow-decision">
            <h4>4. Kiểm tra và Lọc đáp án hợp lệ</h4>
            <p>Nếu đáp án là N/A hoặc sai định dạng A-D -> Chuyển sang luồng Retry</p>
        </div>
        <div class="flow-arrow">↓</div>
        <div class="flow-step">
            <h4>5. Luồng xử lý chuyên sâu (CoT Single & Domain Retry)</h4>
            <p>Ép buộc mô hình suy luận từng bước (Chain-of-Thought) trong thẻ &lt;think&gt;</p>
        </div>
        <div class="flow-arrow">↓</div>
        <div class="flow-step">
            <h4>6. Thích ứng Offline (Offline Auto-Fallback)</h4>
            <p>Tự động ngắt Web Search khi mất mạng để tránh Connection Timeout</p>
        </div>
        <div class="flow-arrow">↓</div>
        <div class="flow-step" style="border-color: #38a169;">
            <h4>7. Xuất file kết quả & Fallback cuối cùng</h4>
            <p>Ghi file pred.csv. Nếu vẫn N/A -> Tự động chọn phương án có số ký tự dài nhất</p>
        </div>
    </div>
    """
    
    # Simple regex block replacement
    mermaid_start = md_content.find("```mermaid")
    mermaid_end = md_content.find("```", mermaid_start + 10)
    if mermaid_start != -1 and mermaid_end != -1:
        md_content = md_content[:mermaid_start] + flowchart_html + md_content[mermaid_end+3:]
        
    # Convert MD to HTML
    html_body = markdown.markdown(md_content, extensions=['fenced_code', 'tables'])
    
    # Full HTML wrapper
    full_html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Báo cáo Phương pháp Atlas Agent</title>
    <style>
        {CSS_STYLE}
    </style>
</head>
<body>
    {html_body}
</body>
</html>
"""
    
    # Save HTML file
    HTML_PATH.write_text(full_html, encoding="utf-8")
    print(f"Generated HTML report at: {HTML_PATH}")
    
    # Call Edge headless to print to PDF
    edge_executable = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_executable):
        edge_executable = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        
    print(f"Converting HTML to PDF using Microsoft Edge...")
    cmd = [
        edge_executable,
        "--headless",
        "--disable-gpu",
        f"--print-to-pdf={PDF_PATH}",
        str(HTML_PATH)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Successfully generated PDF report at: {PDF_PATH}")
        # Clean up temporary HTML file
        if HTML_PATH.exists():
            HTML_PATH.unlink()
            print("Cleaned up temporary HTML file.")
    except Exception as e:
        print(f"Error generating PDF: {e}")
        exit(1)

if __name__ == "__main__":
    generate_pdf()
