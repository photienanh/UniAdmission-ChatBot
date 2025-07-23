from .common import IProcessor, ProcessInput, ProcessedResult
from crawl4ai import MarkdownGenerationResult, DefaultMarkdownGenerator
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from typing import cast

def processs_text(text: str) -> str:
    lines = text.splitlines()
    valid_lines: list[str] = []
    for line in lines:
        line = line.strip()
        if line != "":
            valid_lines.append(line)
    return "\n".join(valid_lines)
class Crawler4AIProcessor(IProcessor):
    def __init__(self) -> None:
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
        parsed: MarkdownGenerationResult = self.generator.generate_markdown(
            input_html=data.text,
            base_url=data.url
        )
        text: str = cast(str, parsed.fit_markdown)
        text = processs_text(text)
        result = ProcessedResult(data.index, data.url, text)
        return result