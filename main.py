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
from crawl4ai.models import MarkdownGenerationResult
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from dotenv import load_dotenv
from schemas import RawCompanyModel

load_dotenv()


class InterceptingMarkdownGenerator:
    def __init__(self, original_generator: DefaultMarkdownGenerator):
        self.original_generator = original_generator

    def generate_markdown(
        self, cleaned_html: str, **kwargs
    ) -> MarkdownGenerationResult:
        markdown_result = self.original_generator.generate_markdown(
            cleaned_html, **kwargs
        )

        modified_fit_markdown = self.custom_processing(markdown_result)
        markdown_result.fit_markdown = modified_fit_markdown

        return markdown_result

    def custom_processing(self, markdown_result: MarkdownGenerationResult) -> str:
        # Implement your custom logic here
        return "Test intercepting" + "\n" + markdown_result.raw_markdown


async def main():
    session_id = "maps_results"
    wait_for_scroll_finish = """js:() => {
        async function autoScroll(containerSelector) {
            const container = document.querySelector(containerSelector);
            if (!container) return false;

            let lastHeight = 0;
            let attempts = 0;
            const maxAttempts = 50; // Safety limit

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
    original_markdown_generator = DefaultMarkdownGenerator()
    intercepting_markdown_generator = InterceptingMarkdownGenerator(
        original_markdown_generator
    )
    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        session_id=session_id,
        # extraction_strategy=llm_strategy,
        only_text=True,
        remove_overlay_elements=True,
        exclude_external_images=True,
        wait_for=wait_for_scroll_finish,
        css_selector="div[role='feed']",
        markdown_generator=intercepting_markdown_generator,
    )

    search_item = "software+company"
    lang = "hl=en&gl=CA"
    city = "Ottawa,+ON"
    query = f"{search_item}+near+{city}"
    url = f"https://www.google.com/maps/search/{query}?{lang}"

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url, config=crawler_config)

        if result.success:
            raw_markdown_file_path = "output/raw_markdown.txt"
            fit_markdown_file_path = "output/fit_markdown.txt"
            os.makedirs(os.path.dirname(raw_markdown_file_path), exist_ok=True)
            os.makedirs(os.path.dirname(fit_markdown_file_path), exist_ok=True)
            with open(raw_markdown_file_path, "w") as file:
                file.write(result.markdown)
            with open(fit_markdown_file_path, "w") as file:
                file.write(result.fit_markdown)

        # llm_strategy.show_usage()
        else:
            print(f"Crawl failed: {result.error_message}")
            print(f"Status code: {result.status_code}")


if __name__ == "__main__":
    asyncio.run(main())
