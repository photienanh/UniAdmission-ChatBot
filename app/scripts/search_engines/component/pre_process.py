from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai import MarkdownGenerationResult, DefaultMarkdownGenerator
from typing import Any, cast
from ..engines import HtmlResult, PreProcessedResult, UrlContent
import re
import requests
URL_PATTERN = re.compile(r'\[(.*?)\]\((.*?)\)', re.DOTALL)
URL_PATTERN_2 = re.compile(r'(?:\*\s|\])\((.*?)\)', re.DOTALL)
# URL_PATTERN = re.compile(r'\[\!\[\]\((.*?)\)\]\((.*?)\)')
URL_PATTERN_REMOVE = re.compile(r'\[.*?\]\(.*?\)', re.DOTALL)
URL_PATTERN_REMOVE_2 = re.compile(r'(?:\*\s|\])\(.*?\)', re.DOTALL)
WHITE_SPACE = re.compile(r'\s+', re.DOTALL)
IMAGE_EXTENSION = (".jpg", ".jpeg", ".png", ".avif", ".webp", ".svg")
# .ico is usually contain no information

def check_pdf(url: str) -> bool:
    """
    This is a little tricky, even download would be hard if it's from drive
    """
    if url.endswith(".pdf"):
        return True
    elif "drive.google.com/file" in url:
        return True # Tempory, as there is hardly anyway to checkd
        # try:
        #     with requests.Session() as session:
        #         response = session.head(url, allow_redirects=True)
        #         print(response.headers)
        #         content_type = response.headers.get("Content-Type", "")
        #         content_disp = response.headers.get("Content-Disposition", "")
        #         print(content_type, content_disp)
        #         if "application/pdf" in content_type.lower():
        #             return True
        #         if ".pdf" in content_disp.lower():
        #             return True
        #         return False
        # except Exception as e:
        #     print(f"Error while check pdf: {url}")
    return False

class PreProcessor:
    def __init__(self) -> None:
        self.filter = None
        """PruningContentFilter(
            threshold=0.5,
            threshold_type="dynamic",
            min_word_threshold=10
        )"""
        self.generator = DefaultMarkdownGenerator(
            content_filter=self.filter,
            options={
                "ignore_links": False,
                "escape_html": True,
                "ignore_images": False,
                "skip_internal_links": False,
                "include_sup_sub": False,
                # "body_width": 80
            }
        )
    def __processs_lines(self, text: str, min_length: int) -> str:
        lines = text.splitlines()
        valid_lines: list[str] = []
        for line in lines:
            line = line.strip()
            solid_line = re.sub(WHITE_SPACE, '', line)
            if solid_line != "" and len(solid_line) > min_length:
                valid_lines.append(line)
        return "\n".join(valid_lines)
    def __process(self, html: str, url: str) -> str:
        parsed: MarkdownGenerationResult = self.generator.generate_markdown(
            input_html=html,
            base_url=url
        )
        text: str = cast(str, parsed.raw_markdown)
        return text
    def __call__(self, input: HtmlResult) -> PreProcessedResult | None:
        raw_markdown = self.__process(input["html"], input["url"])
        raw_markdown = raw_markdown.replace("![]", "[]")
        url_infos: list[tuple[str, str]] = re.findall(URL_PATTERN, raw_markdown)
        fit_markdown = re.sub(URL_PATTERN_REMOVE, "", raw_markdown)
        url_infos.extend([("", url) for url in re.findall(URL_PATTERN_2, fit_markdown)])
        fit_markdown = re.sub(URL_PATTERN_REMOVE_2, "", fit_markdown)
        ref_urls: list[UrlContent] = []
        image_urls: list[UrlContent] = []
        pdf_urls: list[UrlContent] = []
        for title, url in url_infos:
            if check_pdf(url): # To complicated
                pdf_urls.append({
                    "title": title,
                    "url": url
                })
                # raw_markdown = raw_markdown.replace(url, f"PDF_{len(pdf_urls)}", 1)
            elif any(url.endswith(extension) for extension in IMAGE_EXTENSION):
                image_urls.append({
                    "title": title,
                    "url": url
                })
                # raw_markdown = raw_markdown.replace(url, f"IMAGE_{len(image_urls)}", 1)
            else:
                ref_urls.append({
                    "title": title,
                    "url": url
                })
        fit_markdown = self.__processs_lines(fit_markdown, 5)
        result: PreProcessedResult = {
            **input,
            "extracted_content": fit_markdown,
            "ref_urls": ref_urls,
            "image_urls": image_urls,
            "pdf_urls": pdf_urls
        }
        return result
    