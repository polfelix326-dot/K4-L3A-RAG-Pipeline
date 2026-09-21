"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
"""

import os
import json
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CACHE_PATH = Path(__file__).parent.parent / "pageindex_doc_ids.json"


def _load_cache() -> dict[str, str]:
    if not CACHE_PATH.exists():
        return {}
    try:
        value = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _client():
    if not PAGEINDEX_API_KEY:
        return None
    try:
        from pageindex import PageIndexClient
    except ImportError:
        return None
    return PageIndexClient(api_key=PAGEINDEX_API_KEY)


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    client = _client()
    if client is None:
        return
    cache = _load_cache()
    changed = False
    for path in sorted(STANDARDIZED_DIR.parent.joinpath("landing", "legal").glob("*.pdf")):
        source = path.relative_to(STANDARDIZED_DIR.parent.parent).as_posix()
        if source in cache:
            continue
        response = client.submit_document(str(path))
        document_id = response.get("doc_id") or response.get("document_id") or response.get("id")
        if not document_id:
            raise ValueError("PageIndex upload response has no document ID")
        cache[source] = str(document_id)
        changed = True
    if changed:
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _retrieval_items(response: object) -> list[dict]:
    if isinstance(response, list):
        return [item for item in response if isinstance(item, dict)]
    if not isinstance(response, dict):
        return []
    for key in ("results", "retrieval_results", "retrieval_result", "nodes", "items", "data"):
        items = _retrieval_items(response.get(key))
        if items:
            return items
    return []


def _result(item: dict, source: str, rank: int) -> dict | None:
    content = item.get("content") or item.get("text") or item.get("markdown") or item.get("summary")
    if not isinstance(content, str) or not content.strip():
        return None
    score = item.get("score", item.get("relevance", 1 / rank))
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 1 / rank
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    return {
        "id": str(item.get("id") or f"pageindex::{source}::{rank}"),
        "content": content,
        "score": score,
        "metadata": {
            "source": source,
            "title": str(metadata.get("title") or Path(source).stem),
            "doc_type": "legal",
            "url": metadata.get("url"),
            "chunk_index": int(metadata.get("chunk_index", rank - 1)),
        },
        "retrieval_method": "pageindex",
    }


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if top_k <= 0 or not query.strip():
        return []
    client = _client()
    if client is None:
        return []
    try:
        upload_documents()
        cache = _load_cache()
        results = []
        seen = set()
        for source, document_id in cache.items():
            submitted = client.submit_query(document_id, query)
            retrieval_id = submitted.get("retrieval_id") if isinstance(submitted, dict) else None
            response = client.get_retrieval(retrieval_id) if retrieval_id else submitted
            for rank, item in enumerate(_retrieval_items(response), 1):
                result = _result(item, source, rank)
                if result and result["id"] not in seen:
                    seen.add(result["id"])
                    results.append(result)
        results.sort(key=lambda item: (-item["score"], item["id"]))
        return results[:top_k]
    except Exception:
        return []


if __name__ == "__main__":
    upload_documents()
