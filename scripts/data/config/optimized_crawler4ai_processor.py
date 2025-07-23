from .common import IProcessor, ProcessInput, ProcessedResult
from crawl4ai import MarkdownGenerationResult, DefaultMarkdownGenerator
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from bs4 import BeautifulSoup
from typing import cast
def get_approx_count(text: str) -> int:
    soup = BeautifulSoup(text, 'html.parser')
    return len(soup.get_text(strip=True))
def processs_text(text: str) -> str:
    lines = text.splitlines()
    valid_lines: list[str] = []
    for line in lines:
        line = line.strip()
        if line != "":
            valid_lines.append(line)
    return "\n".join(valid_lines)
class OpCrawler4AIProcessor(IProcessor):
    def __init__(self, min_threshold: int = 5000) -> None:
        self.minimum_threshold = min_threshold
        self.filter = PruningContentFilter(
            threshold=0.5,
            threshold_type="dynamic",
            min_word_threshold=10
        )
        self.generator = DefaultMarkdownGenerator(
            content_filter=self.filter,
            options={
                "ignore_links": True,
                "escape_html": True,
                "ignore_images": True,
                "skip_internal_links": False,
                "include_sup_sub": False,
                "body_width": 80
            }
        )
    def process(self, data: ProcessInput) -> ProcessedResult:
        text = ""
        if get_approx_count(data.text) > self.minimum_threshold: 
            parsed: MarkdownGenerationResult = self.generator.generate_markdown(
                input_html=data.text,
                base_url=data.url
            )
            text: str = cast(str, parsed.fit_markdown)
            text = processs_text(text)
        result = ProcessedResult(data.index, data.url, text)
        return result