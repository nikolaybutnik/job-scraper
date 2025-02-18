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
    LLMExtractionStrategy,
)
from dotenv import load_dotenv
from schemas import RawCompanyModel

load_dotenv()


# TODO: need to find a way to wait for scrolling to finish before generating markdown
async def main():
    session_id = "maps_results"
    base_wait = """js:() => {
        const resultItems = document.querySelectorAll('div[role='feed'] > div:not([class])');
        return resultItems.length > 0;
    }"""

    js_scroll = """
        // timeout of 5 seconds per scroll.
        async function autoScroll(containerSelector, delay = 5000) {
            const container = document.querySelector(containerSelector);
            if (!container) {
                console.error("Container not found:", containerSelector);
                return;
            }

            let previousHeight = 0;

            while (true) {
                const resultItems = document.querySelectorAll("div[role='feed'] > div:not([class])");
                console.log("Result count: " + resultItems.length);
                container.scrollTo(0, container.scrollHeight);
                await new Promise(resolve => setTimeout(resolve, delay));

                const newHeight = container.scrollHeight;
                if (newHeight === previousHeight) {
                    console.log("No more content is loading.");
                    break;
                }

                previousHeight = newHeight;
            }
        }

        autoScroll("div[role='feed']");
    """

    proxy_config = {
        "server": os.getenv("PROXY_URL"),
        "username": os.getenv("PROXY_USERNAME"),
        "password": os.getenv("PROXY_PASSWORD"),
    }
    browser_config = BrowserConfig(
        headless=False, verbose=True, proxy_config=proxy_config
    )
    llm_strategy = LLMExtractionStrategy(
        provider="openrouter/deepseek/deepseek-chat:free",
        api_token=os.getenv("DEEPSEEK_API_KEY"),
        schema=RawCompanyModel.schema,
        extraction_type="schema",
        input_format="markdown",
        instruction="For every valid result entry extract company name, address (including street, city, province/state, and country), and website url",
    )
    initial_crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        session_id=session_id,
        extraction_strategy=llm_strategy,
        only_text=True,
        remove_overlay_elements=True,
        exclude_external_images=True,
        wait_for=base_wait,
        js_code=js_scroll,
        # css_selector="div[role='feed']",
    )

    lang = "hl=en&gl=CA"
    city = "Ottawa,+ON"
    query = f"software+company+near+{city}"
    url = f"https://www.google.com/maps/search/{query}?{lang}"

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url, config=initial_crawler_config)

        if result.success:
            print(result.extracted_content)
            print(result.markdown)
            # print(result.extracted_content)

            # llm_strategy.show_usage()
        else:
            print(f"Crawl failed: {result.error_message}")
            print(f"Status code: {result.status_code}")


if __name__ == "__main__":
    asyncio.run(main())
