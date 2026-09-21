"""Normalize landing documents with source URLs, provenance and a corpus hash."""
import hashlib
import json
import re

from markitdown import MarkItDown
import pdfplumber

from src.data_utils import ROOT, atomic_write, read_json, write_json
from src.import_archive import ARCHIVE, validate_landing

LANDING_DIR = ROOT / "data/landing"
OUTPUT_DIR = ROOT / "data/standardized"


def pdf_markdown(path):
    pages = []
    with pdfplumber.open(path) as document:
        for index, page in enumerate(document.pages, 1):
            tables = page.find_tables()
            events = []
            for table in tables:
                rows = []
                for row in table.extract():
                    if rows and all(cell is None for cell in row[:-1]):
                        rows[-1][-1] = "\n".join(filter(None, [rows[-1][-1], row[-1]]))
                    else:
                        rows.append(row)

                def cell(value):
                    return (value or "").replace("|", "\\|").replace("\n", "<br>")

                lines = ["| " + " | ".join(map(cell, row)) + " |" for row in rows]
                lines.insert(1, "| " + " | ".join(["---"] * len(rows[0])) + " |")
                events.append((table.bbox[1], table.bbox[0], "\n".join(lines)))

            def outside_tables(obj):
                if obj.get("object_type") != "char":
                    return True
                x = (obj["x0"] + obj["x1"]) / 2
                y = (obj["top"] + obj["bottom"]) / 2
                return not any(t.bbox[0] <= x <= t.bbox[2] and t.bbox[1] <= y <= t.bbox[3] for t in tables)

            for line in page.filter(outside_tables).extract_text_lines():
                events.append((line["top"], line["x0"], line["text"]))
            text = "\n\n".join(item[2] for item in sorted(events))
            if len(text.strip()) < 30:
                raise ValueError(f"Page {index} needs OCR/manual review: {path}")
            pages.append(f"## Trang {index}\n\n{text}")
    return "\n\n".join(pages)


def render(path, metadata, body):
    body = re.sub(r"\n{3,}", "\n\n", body.replace("\r\n", "\n").replace("\f", "\n")).strip()
    if len(body) < 200:
        raise ValueError(f"Insufficient extracted text: {path}")
    header = {
        "title": metadata["title"],
        "url": metadata["url"],
        "source_page": metadata.get("source_page", metadata["url"]),
        "source_file": path.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "date_crawled": metadata["date_crawled"],
        "source_archive": ARCHIVE.name,
        "archive_sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        "archive_member": path.relative_to(ROOT).as_posix(),
    }
    for key in ("metadata_note", "source_verification", "source_verified_on", "content_start_line", "content_end_line", "normalization"):
        if key in metadata:
            header[key] = metadata[key]
    front = "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in header.items())
    return f"---\n{front}\n---\n\n# {metadata['title']}\n\n{body}\n"


def convert_legal_docs():
    converter = MarkItDown()
    pending = []
    for path in sorted((LANDING_DIR / "legal").iterdir()):
        if path.suffix.lower() not in {".pdf", ".docx", ".doc"}:
            continue
        metadata = read_json(path.with_suffix(".metadata.json"))
        if metadata["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError(f"Landing differs from metadata: {path}")
        body = pdf_markdown(path) if path.suffix.lower() == ".pdf" else converter.convert(str(path)).text_content
        pending.append((OUTPUT_DIR / "legal" / (path.stem + ".md"), render(path, metadata, body)))
    for path, text in pending:
        atomic_write(path, text.encode("utf-8"))


def article_body(markdown):
    lines = markdown.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("# ")), None)
    if start is None:
        raise ValueError("Article has no H1 boundary")
    start += 1
    if start < len(lines) and "/author/" in lines[start]:
        while start < len(lines) and (lines[start].startswith("  * ") or not lines[start].strip()):
            start += 1
    endings = ("[ ![hình đại diện tác giả]", "[Bài trước]", "[Bài tiếp", "### Bài viết liên quan", "Xem thêm:", "### Bài viết cùng chủ đề:")
    end = next((i for i in range(start, len(lines)) if lines[i].startswith(endings)), None)
    if end is None:
        raise ValueError("Article has no recognized end boundary")
    return "\n".join(lines[start:end]), start + 1, end


def convert_news_articles():
    pending = []
    for path in sorted((LANDING_DIR / "news").glob("*.json")):
        data = read_json(path)
        for key in ("url", "title", "date_crawled", "content_markdown"):
            if not isinstance(data.get(key), str) or not data[key].strip():
                raise ValueError(f"Missing {key}: {path}")
        body, start, end = article_body(data["content_markdown"])
        data.update(content_start_line=start, content_end_line=end, normalization="archive article body; navigation/footer removed; whitespace normalized")
        pending.append((OUTPUT_DIR / "news" / (path.stem + ".md"), render(path, data, body)))
    for path, text in pending:
        atomic_write(path, text.encode("utf-8"))


def convert_all():
    records = validate_landing()
    expected = {OUTPUT_DIR / path.relative_to(LANDING_DIR).with_suffix(".md") for path in (ROOT / name for name in records)}
    extra = set(OUTPUT_DIR.rglob("*.md")) - expected
    if extra:
        raise ValueError(f"Standardized contains outputs outside ZIP; archive them first: {extra}")
    convert_legal_docs()
    convert_news_articles()
    files = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUTPUT_DIR.glob("*/*.md"))}
    version = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    write_json(ROOT / "data/corpus_manifest.json", {"source_archive": ARCHIVE.name, "archive_sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(), "landing_files": {name: hashlib.sha256(content).hexdigest() for name, content in sorted(records.items())}, "corpus_sha256": version, "files": files})
    print(f"Saved Markdown to: {OUTPUT_DIR}\nCorpus: {version}")


if __name__ == "__main__":
    convert_all()
