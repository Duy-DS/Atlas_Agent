import os
import subprocess
import sys
from pathlib import Path

# Try importing markdown, install automatically if missing
try:
    import markdown
except ImportError:
    print("[PDFGenerator] Installing markdown package...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"])
    import markdown

DEFAULT_CSS = """
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    line-height: 1.6;
    color: #2d3748;
    max-width: 800px;
    margin: 40px auto;
    padding: 0 20px;
}
h1 {
    color: #1a365d;
    font-size: 2.2em;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 12px;
    margin-top: 40px;
}
h2 {
    color: #2b6cb0;
    font-size: 1.6em;
    margin-top: 30px;
    border-bottom: 1px solid #edf2f7;
    padding-bottom: 6px;
}
h3 {
    color: #4a5568;
    font-size: 1.25em;
    margin-top: 20px;
}
p {
    margin-bottom: 1.2em;
}
code {
    background-color: #f7fafc;
    color: #c53030;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 0.9em;
}
pre {
    background-color: #f7fafc;
    border: 1px solid #e2e8f0;
    padding: 15px;
    border-radius: 6px;
    overflow-x: auto;
    margin-bottom: 1.5em;
}
pre code {
    background-color: transparent;
    color: #2d3748;
    padding: 0;
}
ul, ol {
    padding-left: 20px;
    margin-bottom: 1.5em;
}
li {
    margin-bottom: 6px;
}
blockquote {
    border-left: 4px solid #3182ce;
    padding: 10px 20px;
    margin: 20px 0;
    background-color: #ebf8ff;
    color: #2b6cb0;
    border-radius: 0 6px 6px 0;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 1.5em;
}
th, td {
    padding: 10px 12px;
    border-bottom: 1px solid #e2e8f0;
    text-align: left;
}
th {
    background-color: #f7fafc;
    color: #4a5568;
    font-weight: 600;
}
@media print {
    body {
        margin: 20px;
        font-size: 11pt;
    }
}
"""

def markdown_to_pdf(md_text: str, output_path: Path, title: str = "Report", css_style: str = DEFAULT_CSS):
    """Converts a Markdown string into a premium PDF report using headless Microsoft Edge."""
    # Ensure absolute paths for headless browser printing
    output_path = Path(output_path).resolve()
    
    # Convert markdown to html body
    html_body = markdown.markdown(md_text, extensions=['fenced_code', 'tables'])
    
    # Wrap in HTML template
    full_html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        {css_style}
    </style>
</head>
<body>
    {html_body}
</body>
</html>
"""
    
    # Temporary HTML file path
    temp_html_path = output_path.with_suffix(".html")
    temp_html_path.write_text(full_html, encoding="utf-8")
    
    # Locate Microsoft Edge executable on Windows
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe")
    ]
    
    edge_executable = None
    for p in edge_paths:
        if os.path.exists(p):
            edge_executable = p
            break
            
    if not edge_executable:
        print("[PDFGenerator] Error: Microsoft Edge executable not found. Please install Edge or update paths.")
        return False
        
    print(f"[PDFGenerator] Exporting HTML to PDF using Edge...")
    cmd = [
        edge_executable,
        "--headless",
        "--disable-gpu",
        f"--print-to-pdf={output_path}",
        str(temp_html_path)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"[PDFGenerator] Successfully generated PDF at: {output_path}")
        # Clean up temporary HTML file
        if temp_html_path.exists():
            temp_html_path.unlink()
        return True
    except Exception as e:
        print(f"[PDFGenerator] Failed to generate PDF: {e}")
        return False

if __name__ == "__main__":
    test_md = """
# Báo cáo kết quả phân tích
## 1. Kết quả tóm tắt
Dưới đây là bảng thống kê độ chính xác của các agent:

| Loại Agent | Số câu | Đúng | Độ chính xác |
| :--- | :--- | :--- | :--- |
| Validator | 10 | 10 | 100% |
| Solver | 10 | 9 | 90% |
| Strategist | 10 | 8 | 80% |

> Đây là báo cáo tự động được tạo ra từ hệ thống **AAWB Boilerplate Engine**.
"""
    markdown_to_pdf(test_md, Path("test_report.pdf"), title="Báo cáo kết quả thử nghiệm")
