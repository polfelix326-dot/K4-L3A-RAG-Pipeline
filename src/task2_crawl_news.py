"""
Task 2 — Crawl bài viết/thông báo.

Hướng dẫn:
    1. Điền tối thiểu 5 URL công khai vào ARTICLE_URLS.
    2. Crawl từng URL bằng Crawl4AI.
    3. Lưu mỗi bài thành một JSON trong data/landing/news/.
    4. Giữ đủ url, title, date_crawled và content_markdown.

Cài browser trước khi chạy:
    python -m playwright install chromium
    
-> Dùng Firecrawl or bất cứ công cụ nào bạn quen    
"""

import asyncio
import json
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    # TODO: Thêm ít nhất 5 public URL.
    "https://uet.vnu.edu.vn/chuong-trinh-trao-doi-sinh-vien-tai-dai-hoc-kanazawa-nhat-ban-3/",
    "https://uet.vnu.edu.vn/nop-ho-so-mien-giam-hoc-phi-hoc-ky-i-nam-hoc-2026-2027/",
    "https://css.vnu.edu.vn/dai-hoi-dai-bieu-dang-bo-dhqghn-lan-thu-vii-nhiem-ky-2025-2030-doi-moi-sang-tao-trach-nhiem-quoc-gia-phat-trien-dot-pha/",
    "https://uet.vnu.edu.vn/chuong-trinh-trao-doi-ky-mua-xuan-nam-2027-tai-dai-hoc-osaka-nhat-ban/",
    "https://uet.vnu.edu.vn/to-chuc-tuan-le-hoi-nhap-sinh-vien-nam-hoc-2026-2027/",
    "https://uet.vnu.edu.vn/trieu-tap-nguoi-hoc-tham-du-le-khai-giang-nam-hoc-2026-2027/"
]


async def crawl_article(url: str) -> dict:
    # TODO: Implement crawling logic.
    
    from datetime import datetime
    from crawl4ai import AsyncWebCrawler
    
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        return {
            "url": url,
            "title": result.metadata.get("title", "Unknown"),
            "date_crawled": datetime.now().isoformat(),
            "content_markdown": result.markdown,
        }
    # raise NotImplementedError("Implement crawl_article")


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for index, url in enumerate(ARTICLE_URLS, 1):
        try:
            article = await crawl_article(url)
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved: {output}")
        except Exception as error:
            print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
