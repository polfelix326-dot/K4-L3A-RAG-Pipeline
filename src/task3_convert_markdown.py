"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.

Cài đặt:
    Dependency MarkItDown đã được khai báo trong pyproject.toml.
    
-> Hoặc dùng công cụ nào bạn quen khác Markitdown
"""

from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def convert_legal_docs() -> None:
    """Convert PDF/DOCX vào standardized/legal."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from markitdown import MarkItDown
        converter = MarkItDown()
    except ImportError:
        converter = None

    for path in sorted(legal_dir.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue

        target_file = output_dir / f"{path.stem}.md"
        text_content = ""

        if converter is not None:
            try:
                res = converter.convert(str(path))
                text_content = res.text_content
            except Exception:
                text_content = ""

        if not text_content:
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(str(path))
                pages = [page.get_text() for page in doc]
                text_content = "\n\n".join(pages)
            except Exception:
                pass

        if not text_content and target_file.exists():
            text_content = target_file.read_text(encoding="utf-8")

        if text_content:
            import hashlib
            import json
            if text_content.startswith("---\n"):
                parts = text_content.split("---\n", 2)
                body = parts[2] if len(parts) >= 3 else text_content
            else:
                body = text_content

            sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
            header = (
                f"---\n"
                f"title: {json.dumps(path.stem)}\n"
                f"url: {json.dumps('https://uet.vnu.edu.vn/legal/' + path.name)}\n"
                f"source_file: {json.dumps('data/landing/legal/' + path.name)}\n"
                f"archive_sha256: {json.dumps(sha256)}\n"
                f"---\n\n"
            )
            target_file.write_text(header + body.strip(), encoding="utf-8")


def convert_news_articles() -> None:
    """Convert JSON vào standardized/news."""
    import hashlib
    import json

    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(news_dir.glob("*.json")):
        if path.name.startswith("."):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        header = (
            f"---\n"
            f"title: {json.dumps(data['title'])}\n"
            f"url: {json.dumps(data['url'])}\n"
            f"date_crawled: {json.dumps(data.get('date_crawled', ''))}\n"
            f"source_file: {json.dumps('data/landing/news/' + path.name)}\n"
            f"archive_sha256: {json.dumps(sha256)}\n"
            f"---\n\n"
        )
        content = header + data.get("content_markdown", "").strip()
        (output_dir / f"{path.stem}.md").write_text(content, encoding="utf-8")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
