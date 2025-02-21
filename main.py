# python3 -m venv env
# source env/bin/activate
# deactivate
# pip install -r requirements.txt

import os
import asyncio
import re
from typing import Callable, List, Tuple
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
        """Generates markdown from the cleaned HTML."""
        markdown_result = self.original_generator.generate_markdown(
            cleaned_html, **kwargs
        )

        modified_fit_markdown = self.custom_processing(markdown_result)
        markdown_result.fit_markdown = modified_fit_markdown

        return markdown_result

    def apply_filter(
        self, markdown: str, filter_func: Callable[[str], str], description: str
    ) -> str:
        """Applies a filter function to the markdown and handles errors."""

        try:
            return filter_func(markdown)
        except Exception as e:
            print(f"Error occurred while applying filter '{description}': {e}")
            raise

    def remove_special_characters(self, markdown: str) -> str:
        return re.sub(r"[^a-zA-Z0-9(){}\[\]<>+\-.,\n /:?!_]+", "", markdown)

    def transform_website_format(self, markdown: str) -> str:
        # Handle website links wrapped in Google Maps URLs with special characters
        return re.sub(
            r"\[[^\]]*Website[^\]]*\]\(https?://www\.google\.com/maps/search/<([^>]+)>\)",
            r"[Website](\1)",
            markdown,
            flags=re.IGNORECASE,
        )

    def remove_redundant_data(self, markdown: str) -> str:
        # First pass: Remove unwanted patterns but preserve potential phone numbers
        cleaned = re.sub(
            r"(?im)^\s*\[.*?\]\(https?://www\.google\.com/maps/.*?\)\s*|"  # Google maps links
            r"^.*Directions\b.*|"  # Directions lines
            r"^\s*\d+\.\d+\(\d+\).*|"  # Ratings (4.8(54))
            r"^(Open|Closed)(?![^\n]*(\+?\d{1,3}[-.\s]?)?(\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}).*|"  # Open/Closed without phone
            r"^.*(recommend them!|excellent|Best|services\b|Online appointments).*|"
            r"^(Rating|Hours|All filters|Results|Share).*|"
            r"^[^\\n]*о[^\\n]*|"  # Remove special characters blocks
            r"^\\s*[·•|]\\s*$|"  # Remove separator lines
            r"^\\s*$",  # Remove empty lines
            "",
            markdown,
            flags=re.MULTILINE,
        )

        # Second pass: Extract phone numbers with country codes and varied formats
        cleaned = re.sub(
            r"(?i)(Open|Closed)[^\d\+]*((\+?\d{1,3}[-.\s]?)?(\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4})",
            r"\2",
            cleaned,
            flags=re.MULTILINE,
        )

        # Third pass: Clean up residual characters and empty lines
        cleaned = re.sub(r"[·•|]", " ", cleaned)  # Replace special separators
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def custom_processing(self, markdown_result: MarkdownGenerationResult) -> str:
        """Processes the markdown result by applying a series of filters."""
        filtered_markdown = markdown_result.raw_markdown

        filters: List[Tuple[Callable[[str], str], str]] = [
            (self.transform_website_format, "Transform website format"),
            (self.remove_redundant_data, "Remove redundant data"),
            (self.remove_special_characters, "Remove unnecessary special characters"),
        ]

        for filter_func, description in filters:
            filtered_markdown = self.apply_filter(
                filtered_markdown, filter_func, description
            )

        return filtered_markdown.strip()


async def main():
    session_id = "maps_results"
    wait_for_scroll_finish = """js:() => {
        async function autoScroll(containerSelector) {
            const container = document.querySelector(containerSelector);
            if (!container) return false;

            let lastHeight = 0;
            let attempts = 0;
            const maxAttempts = 5; // Safety limit

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
