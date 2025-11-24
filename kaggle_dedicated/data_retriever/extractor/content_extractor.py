from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai import MarkdownGenerationResult, DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
import re
import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup, NavigableString, Tag, Comment

from ..schema import HtmlResult, WebSource, FileSource
from ..config import FILE_PREFIX
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
    def _extract_html_tables(self, html: str) -> tuple[str, dict[str, str]]:
        """Extract HTML tables and convert to markdown format, replace with placeholders"""
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        table_placeholders = {}
        
        for idx, table in enumerate(tables):
            placeholder = f"[TABLE_{idx}]"
            # Convert table to markdown
            markdown_table = self._html_table_to_markdown(table)
            table_placeholders[placeholder] = markdown_table
            # Replace table with placeholder
            table.replace_with(BeautifulSoup(f'<div>{placeholder}</div>', "html.parser").div)
        
        return str(soup), table_placeholders
    
    def _html_table_to_markdown(self, table) -> str:
        """Convert HTML table to markdown table format"""
        rows = []
        for tr in table.find_all("tr"):
            cells = []
            for cell in tr.find_all(["td", "th"]):
                text = cell.get_text(separator=" ", strip=True)
                # Escape pipe characters
                text = text.replace("|", "\\|")
                cells.append(text)
            if cells:
                rows.append("| " + " | ".join(cells) + " |")
        
        if not rows:
            return ""
        
        # Add header separator for markdown table
        if len(rows) > 0:
            num_cols = len(rows[0].split("|")) - 2  # Subtract empty strings at start/end
            separator = "| " + " | ".join(["---"] * num_cols) + " |"
            # Insert separator after first row (header)
            rows.insert(1, separator)
        
        return "\n".join(rows)
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace while preserving structure"""
        # Preserve double newlines (paragraph breaks)
        # Normalize multiple spaces to single space
        text = re.sub(r'[ \t]+', ' ', text)
        # Normalize 3+ newlines to 2 newlines (paragraph break)
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove trailing whitespace from each line
        lines = [line.rstrip() for line in text.splitlines()]
        return '\n'.join(lines)
    
    def _detect_table_like_data(self, lines: list[str], start_idx: int) -> tuple[bool, int]:
        """
        Detect if lines form a table-like structure (numbered list with consistent pattern).
        Returns (is_table_like, end_idx)
        
        Pattern: lines starting with numbers followed by codes/names/values
        Example: "1 CN1 Công nghệ thông tin 28.19"
        """
        if start_idx >= len(lines):
            return False, start_idx
        
        # Check first line pattern: number + code + name + value
        first_line = lines[start_idx].strip()
        # Pattern: starts with number, has multiple space-separated parts
        if not re.match(r'^\d+\s+[A-Z0-9]', first_line):
            return False, start_idx
        
        # Count consecutive lines with similar pattern
        consecutive_count = 1
        for i in range(start_idx + 1, len(lines)):
            line = lines[i].strip()
            if line == '':
                break
            # Check if line follows similar pattern (starts with number)
            if re.match(r'^\d+\s+', line):
                consecutive_count += 1
            else:
                break
        
        # If we have 3+ consecutive lines with this pattern, it's likely table-like data
        return consecutive_count >= 3, start_idx + consecutive_count
    
    def _convert_table_like_to_markdown_table(self, lines: list[str], start_idx: int, end_idx: int) -> str:
        """Convert table-like numbered list to markdown table format"""
        table_lines = lines[start_idx:end_idx]
        
        # Try to detect columns by splitting on multiple spaces
        rows = []
        for line in table_lines:
            line = line.strip()
            if not line:
                continue
            # Split on 2+ spaces to get columns
            parts = re.split(r'\s{2,}', line)
            if len(parts) >= 2:
                # Remove leading number if present
                if re.match(r'^\d+', parts[0]):
                    parts[0] = re.sub(r'^\d+\s+', '', parts[0], count=1)
                rows.append(parts)
        
        if not rows or len(rows) < 2:
            # Can't form table, return as-is
            return '\n'.join(table_lines)
        
        # Determine number of columns (use max columns from all rows)
        max_cols = max(len(row) for row in rows)
        
        # Normalize rows to have same number of columns
        normalized_rows = []
        for row in rows:
            normalized = row + [''] * (max_cols - len(row))
            normalized_rows.append(normalized[:max_cols])
        
        # Build markdown table
        markdown_table = []
        # Header row (use first row or generic headers)
        if max_cols >= 3:
            header = ['STT', 'Mã', 'Ngành', 'Điểm'] if max_cols == 4 else ['STT'] + [f'Cột {i+1}' for i in range(max_cols-1)]
        else:
            header = [f'Cột {i+1}' for i in range(max_cols)]
        markdown_table.append('| ' + ' | '.join(header) + ' |')
        markdown_table.append('| ' + ' | '.join(['---'] * max_cols) + ' |')
        
        # Data rows
        for row in normalized_rows:
            # Escape pipe characters
            escaped_row = [cell.replace('|', '\\|') for cell in row]
            markdown_table.append('| ' + ' | '.join(escaped_row) + ' |')
        
        return '\n'.join(markdown_table)
    
    def _preserve_lists(self, text: str) -> str:
        """Ensure lists are properly formatted with blank lines, detect and convert table-like data"""
        lines = text.splitlines()
        result = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Check if this is start of table-like data
            is_table_like, end_idx = self._detect_table_like_data(lines, i)
            
            if is_table_like:
                # Convert to markdown table
                if result and result[-1].strip():
                    result.append('')
                result.append('[BẢNG]')
                table_markdown = self._convert_table_like_to_markdown_table(lines, i, end_idx)
                result.append(table_markdown)
                result.append('')
                i = end_idx
                continue
            
            # Regular list item detection
            is_list_item = (line.startswith('- ') or 
                          line.startswith('* ') or
                          line.startswith('+ ') or
                          re.match(r'^\d+[.)]\s+', line))
            
            if is_list_item:
                # Check if previous line was also list item
                if result and result[-1].strip() and not any(
                    result[-1].strip().startswith(marker) 
                    for marker in ['- ', '* ', '+ ']
                ) and not re.match(r'^\d+[.)]\s+', result[-1].strip()):
                    result.append('')
                result.append(lines[i])  # Keep original line (with indentation if any)
            elif line == '':
                if not result or result[-1].strip():
                    result.append('')
            else:
                # Regular text line
                if result and result[-1].strip():
                    # Check if previous was list
                    prev_was_list = any(
                        result[-1].strip().startswith(marker) 
                        for marker in ['- ', '* ', '+ ']
                    ) or re.match(r'^\d+[.)]\s+', result[-1].strip() if result[-1].strip() else '')
                    if prev_was_list:
                        result.append('')
                result.append(lines[i])
            
            i += 1
        
        return '\n'.join(result)
    
    def __processs_lines(self, text: str, min_length: int) -> str:
        """Process lines: filter short lines, normalize whitespace, preserve structure"""
        lines = text.splitlines()
        valid_lines: list[str] = []
        for line in lines:
            line = line.strip()
            solid_line = re.sub(WHITE_SPACE, '', line)
            # Keep lines that are not empty and meet minimum length
            # OR are markdown structure elements (headers, list markers, table separators)
            is_structure = (line.startswith('#') or 
                          line.startswith('- ') or line.startswith('* ') or line.startswith('+ ') or
                          re.match(r'^\d+[.)]\s+', line) or
                          line.startswith('|') or
                          line.startswith('[BẢNG]') or
                          line.startswith('[TABLE'))
            
            if (solid_line != "" and len(solid_line) > min_length) or is_structure:
                valid_lines.append(line)
        
        text = "\n".join(valid_lines)
        # Normalize whitespace while preserving structure
        text = self._normalize_whitespace(text)
        # Preserve list formatting
        text = self._preserve_lists(text)
        return text
    
    def _is_html_content(self, text: str) -> bool:
        """Heuristic: detect whether string contains HTML tags or just plain text"""
        # If there are common HTML tags, treat as HTML
        if "<" in text and ">" in text:
            # Avoid treating math or inequality as tags by checking for </ or <tag
            tag_like = re.search(r'<\s*/?\s*[a-zA-Z][^>]*>', text)
            if tag_like:
                return True
        return False
    
    def _preserve_html_lists(self, html: str) -> str:
        """Ensure HTML unordered/ordered lists keep line-separated items"""
        soup = BeautifulSoup(html, "html.parser")
        list_tags = soup.find_all(["ul", "ol"])
        if not list_tags:
            return html
        for list_tag in list_tags:
            items = []
            for idx, li in enumerate(list_tag.find_all("li", recursive=False), start=1):
                text = li.get_text(" ", strip=True)
                if not text:
                    continue
                if list_tag.name == "ol":
                    prefix = f"{idx}. "
                else:
                    prefix = "- "
                items.append(prefix + text)
            if items:
                replacement = soup.new_string("\n".join(items) + "\n")
                list_tag.replace_with(replacement)
        return str(soup)
    
    def _convert_table(self, table: Tag) -> str:
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if not rows:
            return ""
        header = rows[0]
        body = rows[1:] if len(rows) > 1 else []
        md = "| " + " | ".join(header) + " |\n"
        md += "| " + " | ".join(["---"] * len(header)) + " |\n"
        for row in body:
            md += "| " + " | ".join(row) + " |\n"
        return md.strip()
    
    def _convert_list(self, list_tag: Tag, depth: int = 0) -> str:
        lines: list[str] = []
        for idx, li in enumerate(list_tag.find_all("li", recursive=False), start=1):
            text = li.get_text(" ", strip=True)
            if not text:
                continue
            indent = "  " * depth
            if list_tag.name == "ol":
                prefix = f"{indent}{idx}. "
            else:
                prefix = f"{indent}- "
            lines.append(prefix + text)
            for child in li.children:
                if isinstance(child, Tag) and child.name in ("ul", "ol"):
                    nested = self._convert_list(child, depth + 1)
                    if nested:
                        lines.extend(nested.splitlines())
        return "\n".join(lines)
    
    def _walk_html(self, node: Tag | NavigableString, output: list[str]) -> None:
        if isinstance(node, NavigableString):
            text = str(node).strip()
            if text:
                output.append(text)
            return
        if not isinstance(node, Tag):
            return
        name = node.name.lower()
        if name in ["script", "style", "meta", "header", "footer", "nav", "noscript"]:
            return
        if name in ["h1", "h2", "h3", "h4"]:
            text = node.get_text(separator=" ", strip=True)
            if text:
                level = int(name[1])
                output.append("#" * level + " " + text)
            return
        if name == "p":
            text = node.get_text(separator=" ", strip=True)
            if text:
                output.append(text)
            return
        if name in ["ul", "ol"]:
            lst = self._convert_list(node)
            if lst:
                output.append(lst)
            return
        if name == "table":
            table_md = self._convert_table(node)
            if table_md:
                output.append("[BẢNG]\n" + table_md)
            return
        if name == "br":
            output.append("")
            return
        for child in node.children:
            self._walk_html(child, output)
    
    def _remove_by_selectors(self, soup: BeautifulSoup) -> None:
        selectors = [
            "[class*=breadcrumb]", "#breadcrumbs", ".breadcrumbs",
            ".site-footer", "footer", ".footer", "#footer",
            ".top-bar", ".top-sidebar", ".Top", ".Top.sidebar",
            ".widget-area", ".sidebar", "#sidebar", ".related-posts",
            ".related", ".share-buttons", ".social-links", ".post-meta",
            ".post-navigation", ".content-pad-3x", ".body-wrap #sidebar"
        ]
        for selector in selectors:
            for node in soup.select(selector):
                node.decompose()
        # Remove nav-like unordered lists with too many links
        for tag in soup.find_all(["ul", "ol", "div", "section"]):
            links = tag.find_all("a")
            if len(links) >= 5:
                text = tag.get_text(" ", strip=True)
                link_text = " ".join(a.get_text(" ", strip=True) for a in links)
                if text and len(link_text) / max(len(text), 1) >= 0.75:
                    tag.decompose()

    def _deduplicate_lines(self, text: str) -> str:
        lines = text.splitlines()
        result: list[str] = []
        prev = None
        for line in lines:
            if prev is not None and line.strip() == prev.strip():
                continue
            if line.strip() == "":
                if prev and prev.strip() == "":
                    continue
            result.append(line)
            prev = line
        return "\n".join(result)
    
    def _clean_html_to_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "meta", "header", "footer", "nav", "noscript", "svg"]):
            tag.decompose()
        for element in soup(text=lambda x: isinstance(x, Comment)):
            element.extract()
        self._remove_by_selectors(soup)
        output: list[str] = []
        self._walk_html(soup, output)
        cleaned = "\n".join(chunk for chunk in output if chunk)
        return self._deduplicate_lines(cleaned)
    
    def _extract_content(self, html: str, url: str) -> str:
        # Many upstream steps already clean HTML to plain text. Preserve original line breaks if so.
        if not self._is_html_content(html):
            return self.__processs_lines(html, self._min_line_length)
        
        # Use custom HTML walker to create structured markdown-like text
        structured_text = self._clean_html_to_text(html)
        
        # Fallback to previous method if walker produced nothing
        if not structured_text.strip():
            html_with_lists_preserved = self._preserve_html_lists(html)
            html_with_placeholders, table_placeholders = self._extract_html_tables(html_with_lists_preserved)
            parsed: MarkdownGenerationResult = self.content_generator.generate_markdown(
                input_html=html_with_placeholders,
                base_url=url
            )
            structured_text = parsed.raw_markdown
            structured_text = URL_PATTERN_REMOVE.sub(r'\1', structured_text)
            for placeholder, markdown_table in table_placeholders.items():
                structured_text = structured_text.replace(placeholder, f"\n[BẢNG]\n{markdown_table}\n")
        
        return self.__processs_lines(structured_text, self._min_line_length)
    async def extract(self, html_results: list[HtmlResult], include_pdf: bool) -> list[WebSource]:
        ssl = os.getenv("WEB_SEARCH_SSL", "True").lower() in ("true", "1")
        jobs = []
        for html_result in html_results:
            jobs.append(self._extract_job(ssl, html_result, include_pdf))
        # Use job to maximize files download. (I think extract content can't be speedup even with multi-thread)
        results = await asyncio.gather(*jobs)
        web_sources = []
        for result in results:
            if result:
                web_sources.append(result)
        return web_sources
    async def _extract_job(self, ssl: bool, html_result: HtmlResult, include_pdf: bool) -> WebSource | None:
        links_info = self._extract_links(html_result["html"], html_result["url"])
        main_content = self._extract_content(html_result["html"], html_result["url"])
        # Todo: We can implement a basic link filter based on links_info and main_content
        file_contents: list[FileSource] = []
        pdf_sections: list[str] = []
        if include_pdf:
            file_jobs = []
            for link_info in links_info:
                if link_info["url_type"] == "pdf":
                    file_jobs.append(self._pdf_task(ssl, link_info["title"], link_info["url"]))
                    if len(file_jobs) >= self._max_file_per_page:
                        break
            file_results = await asyncio.gather(*file_jobs)
            for file_result in file_results:
                if file_result:
                    file_contents.append(file_result)
                    pdf_text = file_result["text"].strip()
                    if pdf_text:
                        prefix = FILE_PREFIX.format(
                            title=file_result["file_title"] or "Tài liệu PDF",
                            url=file_result["file_url"]
                        )
                        pdf_sections.append(f"{prefix}{pdf_text}")
        if pdf_sections:
            pdf_block = "\n\n".join(pdf_sections)
            if main_content.strip():
                main_content = f"{main_content}\n\n{pdf_block}"
            else:
                main_content = pdf_block
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
            # Print crawled text for logging
            print(f"\n{'='*80}")
            print(f"[CRAWL TEXT] URL: {web_source['url']}")
            print(f"[CRAWL TEXT] Title: {web_source['title']}")
            print(f"[CRAWL TEXT] Text length: {len(main_content)} characters")
            print(f"[CRAWL TEXT] Text preview (first 500 chars):")
            print("-" * 80)
            preview = main_content[:500] if len(main_content) > 500 else main_content
            print(preview)
            if len(main_content) > 500:
                print(f"... (truncated, total {len(main_content)} chars)")
            print(f"[CRAWL TEXT] Full text:")
            print("-" * 80)
            print(main_content)
            print(f"{'='*80}\n")
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
                        # Print PDF text for logging
                        print(f"\n{'='*80}")
                        print(f"[CRAWL PDF] File URL: {url}")
                        print(f"[CRAWL PDF] File Title: {title}")
                        print(f"[CRAWL PDF] Text length: {len(text)} characters")
                        print(f"[CRAWL PDF] Text preview (first 500 chars):")
                        print("-" * 80)
                        preview = text[:500] if len(text) > 500 else text
                        print(preview)
                        if len(text) > 500:
                            print(f"... (truncated, total {len(text)} chars)")
                        print(f"[CRAWL PDF] Full text:")
                        print("-" * 80)
                        print(text)
                        print(f"{'='*80}\n")
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