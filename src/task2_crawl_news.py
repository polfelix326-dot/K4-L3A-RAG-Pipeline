"""Import every article JSON from k4-day8-data.zip without crawling."""
import asyncio
from src.import_archive import import_branch


async def crawl_all():
    """Legacy entry point: preserves original article metadata and content."""
    import_branch('news')


if __name__ == '__main__':
    asyncio.run(crawl_all())
