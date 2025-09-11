from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai import MarkdownGenerationResult, DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
import re
import os
import asyncio
import aiohttp

from ..schema import HtmlResult, WebSource, FileSource
from .pdf_to_text import PDFProcessor

WHITE_SPACE = re.compile(r'\s+', re.DOTALL)
IMAGE_EXTENSION = (".jpg", ".jpeg", ".png", ".avif", ".webp", ".svg")
URL_PATTERN_REMOVE = re.compile(r'\[([^\]]+)\]\(.*?\)')
# .ico is usually contain no information

def check_pdf(url: str) -> bool:
    """
    This is a little tricky, even download would be hard if it's from drive
    """
    if url.endswith(".pdf"):
        return True
    elif "drive.google.com/file" in url:
        return False # Tempory, as there is hardly anyway to check
    return False

class ContentExtractor:
    def __init__(
        self, 
        session: aiohttp.ClientSession,
        concurrent_file_download: int, 
        timeout: float,
        max_file_per_page: int, 
        min_line_length: int = 5
    ) -> None:
        self._min_line_length = min_line_length
        self._max_file_per_page = max_file_per_page
        self._semaphore = asyncio.Semaphore(concurrent_file_download)
        self.session = session
        self.timeout = aiohttp.ClientTimeout(timeout)
        self.pdf_to_text = PDFProcessor()
        self.content_filter = PruningContentFilter( # This is broken, really
            threshold=0,
            threshold_type="fixed",
            min_word_threshold=1
        )
        self.link_filter = PruningContentFilter( # This is broken, really
            threshold=0.1,
            threshold_type="fixed",
            min_word_threshold=1
        )
        # Filter header, spam content.
        self.content_generator = DefaultMarkdownGenerator(
            content_filter= None, #self.content_filter,
            options={
                "ignore_links": False,
                "escape_html": True,
                "ignore_images": True,
                "skip_internal_links": True,
                "include_sup_sub": False,
                # "body_width": 80
            }
        )
        self.link_generator = DefaultMarkdownGenerator(
            content_filter= None, #self.link_filter,
            options={
                "ignore_links": False,
                "escape_html": True,
                "ignore_images": False,
                "skip_internal_links": True,
                "include_sup_sub": False,
                # "body_width": 80
            }
        )
    def _extract_links(self, html: str, url: str) -> list[dict]:
        markdown = self.link_generator.generate_markdown(
            input_html=html,
            base_url=url   
        ).fit_markdown or ""
        _, citations = self.link_generator.convert_links_to_citations(markdown, url)
        citations = citations.splitlines()
        links: list[dict] = []
        for citation in citations:
            if "⟩" in citation:
                line = citation.split("⟩")[-1].strip()
                if ": " in line:
                    parts = line.split(": ")
                    if len(parts) == 2:
                        url, title = parts
                    else:
                        url = parts[0]
                        title = ": ".join(parts[1:])
                    url = url.strip()
                    title = title.strip()
                else:
                    url = line.strip()
                url_type = "ref"
                if check_pdf(url):
                    url_type = "pdf"
                elif any([url.endswith(extension) for extension in IMAGE_EXTENSION]):
                    url_type = "image"
                links.append({
                    "title": title,
                    "url": url,
                    "url_type": url_type
                })  
        return links
    def __processs_lines(self, text: str, min_length: int) -> str:
        lines = text.splitlines()
        valid_lines: list[str] = []
        for line in lines:
            line = line.strip()
            solid_line = re.sub(WHITE_SPACE, '', line)
            if solid_line != "" and len(solid_line) > min_length:
                valid_lines.append(line)
        return "\n".join(valid_lines)
    def _extract_content(self, html: str, url: str) -> str:
        parsed: MarkdownGenerationResult = self.content_generator.generate_markdown(
            input_html=html,
            base_url=url
        )
        markdown = parsed.raw_markdown
        markdown = URL_PATTERN_REMOVE.sub(r'\1', markdown)
        return self.__processs_lines(markdown, self._min_line_length)
    async def extract(self, html_results: list[HtmlResult]) -> list[WebSource]:
        ssl = os.getenv("WEB_SEARCH_SSL", "True").lower() in ("true", "1")
        jobs = []
        for html_result in html_results:
            jobs.append(self._extract_job(ssl, html_result))
        # Use job to maximize files download. (I think extract content can't be speedup even with multi-thread)
        results = await asyncio.gather(*jobs)
        web_sources = []
        for result in results:
            if result:
                web_sources.append(result)
        return web_sources
    async def _extract_job(self, ssl: bool, html_result: HtmlResult) -> WebSource | None:
        links_info = self._extract_links(html_result["html"], html_result["url"])
        main_content = self._extract_content(html_result["html"], html_result["url"])
        # Todo: We can implement a basic link filter based on links_info and main_content
        file_jobs = []
        for link_info in links_info:
            if link_info["url_type"] == "pdf":
                file_jobs.append(self._pdf_task(ssl, link_info["title"], link_info["url"]))
                if len(file_jobs) >= self._max_file_per_page:
                    break
        file_results = await asyncio.gather(*file_jobs)
        file_contents: list[FileSource] = []
        for file_result in file_results:
            if file_result:
                file_contents.append(file_result)
        web_source: WebSource = {
            "query": html_result["query"],
            "title": html_result["title"],
            "url": html_result["url"],
            "description": html_result["description"],
            "text": main_content,
            "files": file_contents,
            "score": html_result["score"]
        }
        if len(web_source["text"].strip()) != 0 or len(file_contents) != 0:
            return web_source
        else:
            print(f"{web_source['url']} is empty")
                
    async def _pdf_task(self, ssl: bool, title: str, url: str) -> FileSource | None:
        async with self._semaphore:
            try:
                async with self.session.get(url=url, timeout=self.timeout, ssl=ssl) as response:
                    if response.ok:
                        stream = await response.content.read()
                        text = self.pdf_to_text.extract_text(stream)
                        result: FileSource = {
                            "file_title": title,
                            "file_url": url,
                            "file_type": "pdf",
                            "text": text
                        }
                        return result
                    else:
                        print(f"[Page download] Error {response.status}")#: {await response.text()}")
            except asyncio.TimeoutError:
                print(f"[Page downloader] Timeout: {url}")
            except Exception as e:
                print(f"[Page downloader] Error: {str(e)[:100]}")
                # import traceback
                # traceback.print_exc()
            return None