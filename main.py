# python3 -m venv env
# source env/bin/activate
# deactivate
# pip install -r requirements.txt

import os
import asyncio
import json
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    DefaultMarkdownGenerator,
    PruningContentFilter,
)
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from utils import proxy
from dotenv import load_dotenv

load_dotenv()


async def main():
    proxy_config = {
        "server": os.getenv("PROXY_URL"),
        "username": os.getenv("PROXY_USERNAME"),
        "password": os.getenv("PROXY_PASSWORD"),
    }
    print(proxy_config)
    browser_config = BrowserConfig(
        headless=False, verbose=True, proxy_config=proxy_config
    )
    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        process_iframes=False,
        remove_overlay_elements=True,
        exclude_external_links=True,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            "https://news.ycombinator.com/jobs", config=crawler_config
        )

        if result.success:
            print(result.markdown)
        else:
            print(f"Crawl failed: {result.error_message}")
            print(f"Status code: {result.status_code}")


if __name__ == "__main__":
    asyncio.run(main())
