# python3 -m venv env
# source env/bin/activate
# deactivate
# pip install -r requirements.txt

import os
import asyncio
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


async def main():
    session_id = "maps_results"
    wait_for_scroll_finish = """js:() => {
        async function autoScroll(containerSelector) {
            const container = document.querySelector(containerSelector);
            if (!container) return false;

            let lastHeight = 0;
            let attempts = 0;
            const maxAttempts = 100; // Safety limit

            while (attempts < maxAttempts) {
                container.scrollTo(0, container.scrollHeight);
                await new Promise(resolve => setTimeout(resolve, 2000));  // 2 second delay

                const newHeight = container.scrollHeight;
                if (newHeight === lastHeight) {
                    console.log("Reached end of scroll");
                    return true;
                }

                lastHeight = newHeight;
                attempts++;
            }

            return true;
        }

        return autoScroll("div[role='feed']");
    }
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
        instruction="For every entry extract company name, address (including street, city, province/state, and country), and website url. If a piece of data is missing, put None.",
    )
    initial_crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        session_id=session_id,
        extraction_strategy=llm_strategy,
        only_text=True,
        remove_overlay_elements=True,
        exclude_external_images=True,
        wait_for=wait_for_scroll_finish,
        css_selector="div[role='feed']",
    )

    search_item = "software+company"
    lang = "hl=en&gl=CA"
    city = "Ottawa,+ON"
    query = f"{search_item}+near+{city}"
    url = f"https://www.google.com/maps/search/{query}?{lang}"

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url, config=initial_crawler_config)

        if result.success:
            file_path = "output/markdown.txt"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as file:
                file.write(result.markdown)

        # llm_strategy.show_usage()
        else:
            print(f"Crawl failed: {result.error_message}")
            print(f"Status code: {result.status_code}")


if __name__ == "__main__":
    asyncio.run(main())
