from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai import MarkdownGenerationResult, DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
import re
import os
import asyncio
import aiohttp
import unicodedata
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, NavigableString, Tag, Comment

from ..schema import HtmlResult, WebSource, FileSource
from ..config import FILE_PREFIX
from .pdf_to_text import PDFProcessor

WHITE_SPACE = re.compile(r'\s+', re.DOTALL)
IMAGE_EXTENSION = (".jpg", ".jpeg", ".png", ".avif", ".webp", ".svg")
URL_PATTERN_REMOVE = re.compile(r'\[([^\]]+)\]\(.*?\)')
# .ico is usually contain no information

# Keywords để tìm links liên quan đến PDF
KEYWORD_TERMS = [
    "dinh muc", "quy dinh", "huong dan", "muc thu", "hoc phi", "phu luc", "quy trinh", "dinh kem",
    "định mức", "quy định", "hướng dẫn", "mức thu", "học phí", "phụ lục", "quy trình", "đính kèm"
]
MAX_KEYWORD_LINKS = 4
MAX_KEYWORD_WORKERS = 4

def check_pdf(url: str) -> bool:
    """
    This is a little tricky, even download would be hard if it's from drive
    """
    if url.endswith(".pdf"):
        return True
    elif "drive.google.com/file" in url:
        return False # Tempory, as there is hardly anyway to check
    return False

def strip_accents(value: str) -> str:
    """Remove diacritics from Vietnamese text for keyword matching"""
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()

def normalize_internal_link(href: str, base_url: str) -> str:
    """Normalize internal link to full URL"""
    if not href:
        return ""
    href = href.strip()
    if not href or href.startswith("javascript") or href.startswith("mailto:"):
        return ""
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return base_url.rstrip("/") + href
    return urljoin(base_url, href)

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
        markdown_options = {
            "ignore_links": False, "escape_html": True, "skip_internal_links": True, "include_sup_sub": False
        }
        self.content_generator = DefaultMarkdownGenerator(content_filter=None, options={**markdown_options, "ignore_images": True})
        self.link_generator = DefaultMarkdownGenerator(content_filter=None, options={**markdown_options, "ignore_images": True})
        self.link_generator = DefaultMarkdownGenerator(content_filter=None, options={**markdown_options, "ignore_images": False})
    def _find_keyword_links(self, html: str, base_url: str, max_links: int = MAX_KEYWORD_LINKS) -> list[str]:
        """Tìm links có chứa keywords"""
        soup = BeautifulSoup(html, "html.parser")
        links, seen = [], set()
        for a in soup.find_all("a", href=True):
            if len(links) >= max_links:
                break
            href = a.get("href", "").strip()
            if not href or href.startswith("#"):
                continue
            target = normalize_internal_link(href, base_url)
            if not target or target in seen:
                continue
            meta = " ".join(filter(None, [a.get_text(" ", strip=True), a.get("title"), href]))
            if any(term in strip_accents(meta) for term in KEYWORD_TERMS):
                links.append(target)
                seen.add(target)
        return links
    
    def _find_attachment_links(self, html: str, base_url: str) -> list[dict]:
        """Tìm links 'đính kèm' trong HTML"""
        soup = BeautifulSoup(html, "html.parser")
        keywords = ["đính kèm", "dinh kem", "file đính kèm", "tải về", "tai ve", "download"]
        links, seen = [], set()
        all_links_count = 0
        for a in soup.find_all("a", href=True):
            all_links_count += 1
            href = a.get("href", "").strip()
            if not href or href.startswith("#"):
                continue
            target = normalize_internal_link(href, base_url)
            if not target or target in seen:
                continue
            text = a.get_text(" ", strip=True)
            title = a.get("title", "")
            meta = " ".join([text, title, href]).lower()
            meta_normalized = strip_accents(meta)
            # Kiểm tra keyword
            matched_keywords = [kw for kw in keywords if kw in meta_normalized]
            if matched_keywords:
                is_pdf = check_pdf(target)
                link_info = {
                    "url": target,
                    "title": text or title or target.split("/")[-1],
                    "is_pdf": is_pdf
                }
                links.append(link_info)
                seen.add(target)
                print(f"[Attachment search] Tìm thấy: '{text[:50]}' -> {target[:80]} (PDF: {is_pdf}, keyword: {matched_keywords[0]})")
        print(f"[Attachment search] Tổng số links kiểm tra: {all_links_count}, tìm thấy: {len(links)}")
        return links
    
    async def _crawl_keyword_links(self, links: list[str], ssl: bool) -> list[FileSource]:
        """Crawl keyword links để tìm PDF"""
        if not links:
            return []
        
        print(f"[Keyword crawl] Đang crawl {len(links)} keyword links:")
        for idx, link in enumerate(links, 1):
            print(f"[Keyword crawl]   [{idx}] {link}")
        
        async def process_link(link_url: str) -> FileSource | None:
            try:
                print(f"[Keyword crawl] → Crawling: {link_url}")
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                async with self.session.get(url=link_url, timeout=self.timeout, ssl=ssl, headers=headers) as response:
                    if response.ok:
                        html = await response.text()
                        pdf_links = [li for li in self._extract_links(html, link_url) if li["url_type"] == "pdf"]
                        print(f"[Keyword crawl]   → Tìm thấy {len(pdf_links)} PDF links trực tiếp")
                        if not pdf_links:
                            att_links = self._find_attachment_links(html, link_url)
                            print(f"[Keyword crawl]   → Tìm thấy {len(att_links)} attachment links")
                            pdf_att = [att for att in att_links if att["is_pdf"]]
                            print(f"[Keyword crawl]   → PDF từ attachment: {len(pdf_att)}")
                            pdf_links = [{"title": att["title"], "url": att["url"]} for att in pdf_att]
                        if pdf_links:
                            print(f"[Keyword crawl]   → Đang tải PDF: {pdf_links[0]['url']}")
                            result = await self._pdf_task(ssl, pdf_links[0]["title"], pdf_links[0]["url"])
                            if result:
                                print(f"[Keyword crawl]   ✓ Thành công: {link_url[:50]}...")
                            return result
                        else:
                            print(f"[Keyword crawl]   ✗ Không tìm thấy PDF trong: {link_url[:50]}...")
            except Exception as e:
                print(f"[Keyword crawl]   ✗ Error {link_url[:50]}...: {str(e)[:50]}")
            return None
        
        semaphore = asyncio.Semaphore(min(MAX_KEYWORD_WORKERS, len(links)) or 1)
        async def bounded(link_url: str):
            async with semaphore:
                return await process_link(link_url)
        results = await asyncio.gather(*[bounded(link) for link in links])
        pdfs = [r for r in results if r]
        print(f"[Keyword crawl] Kết quả: {len(pdfs)}/{len(links)} PDFs found\n")
        return pdfs
    
    async def _crawl_attachment_links(self, attachment_links: list[dict], ssl: bool) -> list[FileSource]:
        """Crawl attachment links để tìm PDF"""
        if not attachment_links:
            return []
        
        # Lọc ra các link không phải PDF để crawl
        non_pdf_links = [att for att in attachment_links if not att["is_pdf"]]
        pdf_links = [att for att in attachment_links if att["is_pdf"]]
        
        print(f"[Attachment crawl] Đang crawl {len(non_pdf_links)} non-PDF attachment links:")
        for idx, att in enumerate(non_pdf_links, 1):
            print(f"[Attachment crawl]   [{idx}] {att['title']}: {att['url']}")
        
        async def process_attachment(att: dict) -> FileSource | None:
            try:
                print(f"[Attachment crawl] → Crawling: {att['url']}")
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                async with self.session.get(url=att["url"], timeout=self.timeout, ssl=ssl, headers=headers, allow_redirects=True) as response:
                    # Kiểm tra Content-Type trước
                    content_type = response.headers.get("Content-Type", "").lower()
                    if "application/pdf" in content_type:
                        print(f"[Attachment crawl]   → Response là PDF trực tiếp (Content-Type: {content_type})")
                        # Tải PDF trực tiếp
                        pdf_data = await response.read()
                        if pdf_data:
                            result = FileSource(
                                title=att["title"],
                                url=att["url"],
                                content=self.pdf_to_text.extract_text(pdf_data, include_metadata=False),
                                file_type="pdf"
                            )
                            print(f"[Attachment crawl]   ✓ Thành công: {att['url'][:50]}...")
                            return result
                    
                    if response.ok:
                        html = await response.text()
                        pdf_links = [li for li in self._extract_links(html, att["url"]) if li["url_type"] == "pdf"]
                        print(f"[Attachment crawl]   → Tìm thấy {len(pdf_links)} PDF links trong HTML")
                        if pdf_links:
                            print(f"[Attachment crawl]   → Đang tải PDF: {pdf_links[0]['url']}")
                            result = await self._pdf_task(ssl, pdf_links[0]["title"], pdf_links[0]["url"])
                            if result:
                                print(f"[Attachment crawl]   ✓ Thành công: {att['url'][:50]}...")
                            return result
                        else:
                            print(f"[Attachment crawl]   ✗ Không tìm thấy PDF trong: {att['url'][:50]}...")
            except Exception as e:
                print(f"[Attachment crawl]   ✗ Error {att['url'][:50]}...: {str(e)[:50]}")
            return None
        
        # Xử lý PDF links trực tiếp trước
        pdf_results = []
        for att in pdf_links:
            print(f"[Attachment crawl] → Tải PDF trực tiếp: {att['url']}")
            result = await self._pdf_task(ssl, att["title"], att["url"])
            if result:
                pdf_results.append(result)
                print(f"[Attachment crawl]   ✓ Thành công: {att['url'][:50]}...")
        
        # Crawl non-PDF links
        if non_pdf_links:
            semaphore = asyncio.Semaphore(min(MAX_KEYWORD_WORKERS, len(non_pdf_links)) or 1)
            async def bounded(att: dict):
                async with semaphore:
                    return await process_attachment(att)
            results = await asyncio.gather(*[bounded(att) for att in non_pdf_links])
            pdf_results.extend([r for r in results if r])
        
        print(f"[Attachment crawl] Kết quả: {len(pdf_results)}/{len(attachment_links)} PDFs found\n")
        return pdf_results
    
    def _extract_links(self, html: str, url: str) -> list[dict]:
        """Extract links from HTML - tìm PDF trực tiếp từ HTML trước"""
        links = []
        seen = set()
        
        # 1. Tìm PDF links trực tiếp từ HTML (giống code mẫu)
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            raw = a.get("href", "").strip()
            if not raw or raw.startswith("#"):
                continue
            
            # Normalize URL
            if raw.lower().endswith(".pdf"):
                if raw.startswith("http"):
                    pdf_url = raw
                else:
                    pdf_url = url.rstrip("/") + "/" + raw.lstrip("/")
                
                if pdf_url not in seen:
                    seen.add(pdf_url)
                    links.append({
                        "title": a.get_text(" ", strip=True) or pdf_url.split("/")[-1],
                        "url": pdf_url,
                        "url_type": "pdf"
                    })
        
        # 2. Tìm các links khác từ crawl4ai (nếu cần)
        if len(links) < 10:  # Chỉ dùng crawl4ai nếu chưa tìm đủ links
            try:
                markdown = self.link_generator.generate_markdown(input_html=html, base_url=url).fit_markdown or ""
                _, citations = self.link_generator.convert_links_to_citations(markdown, url)
                for citation in citations.splitlines():
                    if "⟩" not in citation:
                        continue
                    line = citation.split("⟩")[-1].strip()
                    parts = line.split(": ", 1) if ": " in line else [line, ""]
                    link_url, title = parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""
                    if link_url in seen:
                        continue
                    seen.add(link_url)
                    url_type = "pdf" if check_pdf(link_url) else ("image" if any(link_url.endswith(ext) for ext in IMAGE_EXTENSION) else "ref")
                    links.append({"title": title, "url": link_url, "url_type": url_type})
            except Exception as e:
                print(f"[Link extract] Lỗi crawl4ai: {str(e)[:50]}")
        
        return links
    def _convert_table_to_markdown(self, table: Tag) -> str:
        """Convert HTML table to markdown format - viết lại từ đầu"""
        rows = []
        for tr in table.find_all("tr"):
            cells = []
            for cell in tr.find_all(["td", "th"]):
                # Lấy text, clean và escape pipe
                text = cell.get_text(" ", strip=True)
                text = self._clean_cell_text(text)
                # Xóa ** (bold markdown)
                text = re.sub(r'\*\*', '', text)
                text = text.replace("|", "\\|")
                cells.append(text)
            if cells:
                rows.append(cells)
        
        if not rows:
            return ""
        
        # Xóa các cột trống ở đầu và cuối của tất cả rows
        if rows:
            # Tìm cột đầu tiên và cuối cùng có nội dung
            first_col = 0
            last_col = max(len(row) for row in rows) - 1
            
            # Tìm cột đầu tiên có nội dung
            for i in range(len(rows[0])):
                if any(row[i].strip() if i < len(row) else False for row in rows):
                    first_col = i
                    break
            
            # Tìm cột cuối cùng có nội dung
            for i in range(len(rows[0]) - 1, -1, -1):
                if any(row[i].strip() if i < len(row) else False for row in rows):
                    last_col = i
                    break
            
            # Trim rows
            trimmed_rows = []
            for row in rows:
                if first_col < len(row):
                    trimmed_row = row[first_col:last_col+1]
                    trimmed_rows.append(trimmed_row)
                else:
                    trimmed_rows.append([])
            rows = trimmed_rows
        
        # Tạo markdown table
        markdown_lines = []
        # Header row (first row)
        if rows:
            header = rows[0]
            if header:
                markdown_lines.append("| " + " | ".join(header) + " |")
                # Separator
                markdown_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
                # Data rows
                for row in rows[1:]:
                    # Pad row nếu thiếu columns
                    while len(row) < len(header):
                        row.append("")
                    # Trim nếu thừa columns
                    row = row[:len(header)]
                    markdown_lines.append("| " + " | ".join(row) + " |")
        
        return "\n".join(markdown_lines)
    
    def _clean_cell_text(self, text: str) -> str:
        """Làm sạch text trong cell: gộp các dòng xuống dòng thành 1 dòng, xóa khoảng trắng thừa"""
        if not text:
            return ""
        text = str(text).strip()
        # Thay thế tất cả các ký tự whitespace (bao gồm \n, \r, \t, space) bằng 1 space duy nhất
        # Đảm bảo mọi xuống dòng đều được gộp thành 1 dòng
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace - giữ table format, gộp inline metadata"""
        lines = text.splitlines()
        result = []
        in_table = False
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Phát hiện table block - bỏ qua nếu trùng lặp
            if stripped == '[BẢNG]':
                if not (result and result[-1].strip() == '[BẢNG]'):
                    in_table = True
                    result.append('[BẢNG]')
                i += 1
                continue
            
            # Trong table: giữ nguyên format, nhưng clean cell text
            if in_table:
                if stripped.startswith('|'):
                    # Kiểm tra xem có phải separator row không
                    if '---' in stripped:
                        # Separator row: chỉ thêm nếu chưa có separator row ngay trước đó
                        if not (result and result[-1].startswith('|') and '---' in result[-1]):
                            # Đếm số cột từ dòng trước (nếu có)
                            num_cols = 0
                            if result and result[-1].startswith('|') and '---' not in result[-1]:
                                prev_cells = result[-1].split('|')
                                prev_cleaned = [c.strip() for c in prev_cells if c.strip()]
                                num_cols = len(prev_cleaned)
                            else:
                                # Nếu không có dòng trước, đếm từ dòng hiện tại
                                cells = stripped.split('|')
                                num_cols = len([c for c in cells if '---' in c or c.strip() == ''])
                            
                            if num_cols > 0:
                                separator = '|' + '|'.join(['---'] * num_cols) + '|'
                                result.append(separator)
                        # Bỏ qua separator row trùng lặp
                    else:
                        # Data row: clean từng cell
                        cells = stripped.split('|')
                        cleaned_cells = []
                        for cell in cells:
                            # Clean cell: xóa HTML tags (<br>), xóa ** (bold markdown), gộp whitespace thành 1 space
                            cleaned_cell = re.sub(r'<[^>]+>', '', cell)  # Xóa HTML tags
                            cleaned_cell = re.sub(r'\*\*', '', cleaned_cell)  # Xóa **
                            cleaned_cell = re.sub(r'\s+', ' ', cleaned_cell.strip())
                            cleaned_cells.append(cleaned_cell)
                        
                        # Xóa các cột trống ở đầu và cuối
                        while cleaned_cells and not cleaned_cells[0].strip():
                            cleaned_cells.pop(0)
                        while cleaned_cells and not cleaned_cells[-1].strip():
                            cleaned_cells.pop()
                        
                        if cleaned_cells:
                            row = '|' + '|'.join(cleaned_cells) + '|'
                            result.append(row)
                            
                            # Nếu đây là header row (dòng đầu tiên sau [BẢNG]), đảm bảo có separator
                            if len(result) >= 2 and result[-2] == '[BẢNG]':
                                # Đếm số cột
                                num_cols = len([c for c in cleaned_cells if c.strip()])
                                if num_cols > 0:
                                    separator = '|' + '|'.join(['---'] * num_cols) + '|'
                                    result.append(separator)
                elif not stripped:
                    # Bỏ qua dòng trống trong table
                    pass
                elif stripped.isdigit() or (stripped == '---' and not stripped.startswith('|')):
                    # Bỏ qua các dòng chỉ có số hoặc dấu --- đơn lẻ (không phải separator row)
                    pass
                else:
                    # Kết thúc table
                    in_table = False
                    # Xử lý dòng này như bình thường
                    if stripped:
                        cleaned = re.sub(r'<[^>]+>', '', stripped)  # Xóa HTML tags
                        cleaned = re.sub(r'\s+', ' ', cleaned)
                        result.append(cleaned)
                i += 1
                continue
            
            # Gộp inline metadata: các dòng ngắn liên tiếp (có thể có | hoặc ·)
            if stripped and not stripped.startswith('|') and len(stripped) < 150:
                metadata_lines = [stripped]
                j = i + 1
                # Gộp các dòng ngắn liên tiếp (dừng khi gặp dòng dài hoặc structure)
                while j < len(lines):
                    next_stripped = lines[j].strip()
                    if not next_stripped or len(next_stripped) > 150 or next_stripped.startswith(('#', '- ', '* ', '[BẢNG]')):
                        break
                    metadata_lines.append(next_stripped)
                    j += 1
                
                # Gộp thành 1 dòng: xử lý | và ·
                # Nếu có dòng chỉ là "|", gộp với dòng trước/sau
                parts = []
                for line in metadata_lines:
                    line = line.replace('·', '|').strip()
                    if line == '|':
                        # Dòng chỉ có |, bỏ qua (sẽ được normalize sau)
                        continue
                    # Nếu dòng có |, tách ra
                    if '|' in line:
                        parts.extend(p.strip() for p in line.split('|') if p.strip())
                    else:
                        # Dòng không có |, thêm vào phần cuối hoặc tạo mới
                        if parts:
                            parts[-1] = (parts[-1] + ' ' + line).strip()
                        else:
                            parts.append(line)
                
                # Join bằng |
                if parts:
                    merged = ' | '.join(parts)
                    result.append(merged)
                i = j
                continue
            
            # Dòng thường: normalize spaces (gộp tất cả whitespace thành 1 space)
            if stripped:
                cleaned = re.sub(r'\s+', ' ', stripped)
                result.append(cleaned)
            elif result and result[-1] and result[-1].strip():
                # Chỉ thêm dòng trống nếu dòng trước không phải dòng trống
                result.append('')
            i += 1
        
        # Xóa tất cả dòng trống thừa giữa text với text
        final_result = []
        for i, line in enumerate(result):
            if line.strip():
                final_result.append(line)
            # Bỏ qua tất cả dòng trống
        
        text = '\n'.join(final_result)
        # Xóa dòng trống ở đầu và cuối
        text = text.strip()
        return text
    
    def _detect_table_like_data(self, lines: list[str], start_idx: int) -> tuple[bool, int]:
        """Detect table-like numbered list pattern"""
        if start_idx >= len(lines) or not re.match(r'^\d+\s+[A-Z0-9]', lines[start_idx].strip()):
            return False, start_idx
        count = 1
        for i in range(start_idx + 1, len(lines)):
            if not lines[i].strip() or not re.match(r'^\d+\s+', lines[i].strip()):
                break
            count += 1
        return count >= 3, start_idx + count
    
    def _convert_table_like_to_markdown_table(self, lines: list[str], start_idx: int, end_idx: int) -> str:
        """Convert table-like numbered list to markdown"""
        rows = []
        for line in lines[start_idx:end_idx]:
            parts = re.split(r'\s{2,}', line.strip())
            if len(parts) >= 2:
                if re.match(r'^\d+', parts[0]):
                    parts[0] = re.sub(r'^\d+\s+', '', parts[0], count=1)
                rows.append(parts)
        if not rows or len(rows) < 2:
            return '\n'.join(lines[start_idx:end_idx])
        max_cols = max(len(row) for row in rows)
        normalized = [row + [''] * (max_cols - len(row)) for row in rows]
        header = ['STT', 'Mã', 'Ngành', 'Điểm'] if max_cols == 4 else (['STT'] + [f'Cột {i+1}' for i in range(max_cols-1)] if max_cols >= 3 else [f'Cột {i+1}' for i in range(max_cols)])
        md = ['| ' + ' | '.join(header) + ' |', '| ' + ' | '.join(['---'] * max_cols) + ' |']
        md.extend('| ' + ' | '.join(cell.replace('|', '\\|') for cell in row[:max_cols]) + ' |' for row in normalized)
        return '\n'.join(md)
    
    def _preserve_lists(self, text: str) -> str:
        """Format lists và detect table-like data"""
        lines = text.splitlines()
        result = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            is_table_like, end_idx = self._detect_table_like_data(lines, i)
            if is_table_like:
                if result and result[-1].strip():
                    result.append('')
                result.extend(['[BẢNG]', self._convert_table_like_to_markdown_table(lines, i, end_idx)])
                i = end_idx
                continue
            is_list = line.startswith(('- ', '* ', '+ ')) or re.match(r'^\d+[.)]\s+', line)
            if is_list:
                if result and result[-1].strip() and not (result[-1].strip().startswith(('- ', '* ', '+ ')) or re.match(r'^\d+[.)]\s+', result[-1].strip())):
                    result.append('')
                result.append(lines[i])
            elif line == '':
                # Chỉ thêm dòng trống nếu cần
                if result and result[-1].strip():
                    result.append('')
            else:
                prev_list = result and (result[-1].strip().startswith(('- ', '* ', '+ ')) or re.match(r'^\d+[.)]\s+', result[-1].strip() if result[-1].strip() else ''))
                if prev_list:
                    result.append('')
                result.append(lines[i])
            i += 1
        # Xóa dòng trống thừa
        text = '\n'.join(result)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    
    def __processs_lines(self, text: str, min_length: int) -> str:
        """Process lines: filter, normalize, preserve structure - giữ table format"""
        lines = text.splitlines()
        valid_lines = []
        in_table = False
        structure_markers = ('#', '- ', '* ', '+ ', '|', '[BẢNG]')
        
        for original_line in lines:
            line = original_line.strip()
            solid_line = re.sub(WHITE_SPACE, '', line)
            
            # Table block detection - bỏ qua nếu trùng lặp
            if line == '[BẢNG]':
                if not (valid_lines and valid_lines[-1].strip() == '[BẢNG]'):
                    in_table = True
                    # Không thêm dòng trống trước [BẢNG] nếu dòng trước cũng là structure
                    if valid_lines and valid_lines[-1].strip() and not valid_lines[-1].strip().startswith(('[BẢNG]', '|')):
                        valid_lines.append('')
                    valid_lines.append('[BẢNG]')
            elif in_table:
                # Trong table: giữ format nhưng clean cell text
                if line.startswith('|'):
                    # Kiểm tra xem có phải separator row không
                    if '---' in line:
                        # Separator row: chỉ thêm nếu chưa có separator row ngay trước đó
                        if not (valid_lines and valid_lines[-1].startswith('|') and '---' in valid_lines[-1]):
                            # Đếm số cột từ dòng trước (nếu có)
                            num_cols = 0
                            if valid_lines and valid_lines[-1].startswith('|') and '---' not in valid_lines[-1]:
                                prev_cells = valid_lines[-1].split('|')
                                prev_cleaned = [c.strip() for c in prev_cells if c.strip()]
                                num_cols = len(prev_cleaned)
                            else:
                                # Nếu không có dòng trước, đếm từ dòng hiện tại
                                cells = line.split('|')
                                num_cols = len([c for c in cells if '---' in c or c.strip() == ''])
                            
                            if num_cols > 0:
                                separator = '|' + '|'.join(['---'] * num_cols) + '|'
                                valid_lines.append(separator)
                        # Bỏ qua separator row trùng lặp
                    else:
                        # Data row: clean từng cell
                        cells = line.split('|')
                        cleaned_cells = []
                        for cell in cells:
                            # Xóa ** (bold markdown)
                            cleaned_cell = re.sub(r'\*\*', '', cell)
                            cleaned_cell = re.sub(r'\s+', ' ', cleaned_cell.strip())
                            cleaned_cells.append(cleaned_cell)
                        
                        # Xóa các cột trống ở đầu và cuối
                        while cleaned_cells and not cleaned_cells[0].strip():
                            cleaned_cells.pop(0)
                        while cleaned_cells and not cleaned_cells[-1].strip():
                            cleaned_cells.pop()
                        
                        if cleaned_cells:
                            row = '|' + '|'.join(cleaned_cells) + '|'
                            valid_lines.append(row)
                            
                            # Nếu đây là header row (dòng đầu tiên sau [BẢNG]), đảm bảo có separator
                            if len(valid_lines) >= 2 and valid_lines[-2] == '[BẢNG]':
                                num_cols = len([c for c in cleaned_cells if c.strip()])
                                if num_cols > 0:
                                    separator = '|' + '|'.join(['---'] * num_cols) + '|'
                                    valid_lines.append(separator)
                elif not line:
                    # Bỏ qua dòng trống trong table
                    pass
                else:
                    # Kết thúc table
                    in_table = False
                    if (solid_line and len(solid_line) > min_length) or line.startswith(structure_markers):
                        cleaned = re.sub(r'\s+', ' ', line)
                        valid_lines.append(cleaned)
            # Dòng thường
            elif line.startswith(structure_markers) or (solid_line and len(solid_line) > min_length):
                valid_lines.append(line)
        
        text = "\n".join(valid_lines)
        text = self._normalize_whitespace(text)
        text = self._preserve_lists(text)
        # Xóa dòng trống thừa cuối cùng
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
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
        """Convert table tag to markdown"""
        return self._convert_table_to_markdown(table)
    
    def _convert_list(self, list_tag: Tag, depth: int = 0) -> str:
        lines: list[str] = []
        for idx, li in enumerate(list_tag.find_all("li", recursive=False), start=1):
            text = li.get_text(" ", strip=True)
            if not text:
                continue
            # Clean text: xóa khoảng trắng thừa
            text = self._clean_cell_text(text)
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
                # Clean text: xóa khoảng trắng thừa
                text = self._clean_cell_text(text)
                level = int(name[1])
                output.append("#" * level + " " + text)
            return
        if name == "p":
            text = node.get_text(separator=" ", strip=True)
            if text:
                # Clean text: xóa khoảng trắng thừa
                text = self._clean_cell_text(text)
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
                output.append("[BẢNG]")
                # Thêm từng dòng của table để dễ xử lý
                for line in table_md.splitlines():
                    output.append(line)
            return
        if name == "br":
            output.append("")
            return
        for child in node.children:
            self._walk_html(child, output)
    
    def _remove_by_selectors(self, soup: BeautifulSoup) -> None:
        """Remove unwanted elements"""
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
        # Remove nav-like lists with too many links
        for tag in soup.find_all(["ul", "ol", "div", "section"]):
            links = tag.find_all("a")
            if len(links) >= 5:
                text = tag.get_text(" ", strip=True)
                if text and len(" ".join(a.get_text(" ", strip=True) for a in links)) / max(len(text), 1) >= 0.75:
                    tag.decompose()

    def _clean_html_to_text(self, html: str) -> str:
        """Clean HTML to text, giữ table format"""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "meta", "header", "footer", "nav", "noscript", "svg"]):
            tag.decompose()
        for element in soup(text=lambda x: isinstance(x, Comment)):
            element.extract()
        self._remove_by_selectors(soup)
        output = []
        self._walk_html(soup, output)
        return "\n".join(chunk for chunk in output if chunk)
    
    def _extract_content(self, html: str, url: str) -> str:
        """Extract content from HTML"""
        if not self._is_html_content(html):
            return self.__processs_lines(html, self._min_line_length)
        
        structured_text = self._clean_html_to_text(html)
        
        if not structured_text.strip():
            # Fallback: crawl4ai markdown generator
            html_with_lists = self._preserve_html_lists(html)
            soup = BeautifulSoup(html_with_lists, "html.parser")
            table_placeholders = {}
            for idx, table in enumerate(soup.find_all("table")):
                placeholder = f"[TABLE_{idx}]"
                table_placeholders[placeholder] = self._convert_table_to_markdown(table)
                table.replace_with(BeautifulSoup(f'<div>{placeholder}</div>', "html.parser").div)
            
            parsed: MarkdownGenerationResult = self.content_generator.generate_markdown(input_html=str(soup), base_url=url)
            structured_text = URL_PATTERN_REMOVE.sub(r'\1', parsed.raw_markdown)
            for placeholder, table_md in table_placeholders.items():
                structured_text = structured_text.replace(placeholder, f"\n[BẢNG]\n{table_md}\n")
        
        processed = self.__processs_lines(structured_text, self._min_line_length)
        return re.sub(r'\n{3,}', '\n\n', processed)
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
        file_contents: list[FileSource] = []
        pdf_links = []
        if include_pdf:
            print(f"\n[PDF SEARCH] Đang tìm PDF trong: {html_result['url']}")
            print(f"[PDF SEARCH] Tổng số links tìm thấy: {len(links_info)}")
            
            # Đếm số PDF links
            direct_pdf_links = [li for li in links_info if li["url_type"] == "pdf"]
            print(f"[PDF SEARCH] PDF links trực tiếp từ links: {len(direct_pdf_links)}")
            if direct_pdf_links:
                for pdf_link in direct_pdf_links:
                    print(f"[PDF SEARCH]   - {pdf_link['title']}: {pdf_link['url']}")
            
            file_jobs = []
            # 1. Tìm PDF trực tiếp từ links
            for link_info in links_info:
                if link_info["url_type"] == "pdf":
                    file_jobs.append(self._pdf_task(ssl, link_info["title"], link_info["url"]))
                    pdf_links.append(link_info["url"])
                    if len(file_jobs) >= self._max_file_per_page:
                        break
            
            # 2. Tìm PDF từ links "đính kèm"
            attachment_links = self._find_attachment_links(html_result["html"], html_result["url"])
            print(f"[PDF SEARCH] Attachment links tìm thấy: {len(attachment_links)}")
            
            # Ưu tiên PDF trực tiếp từ attachment
            pdf_attachments = [att for att in attachment_links if att["is_pdf"] and att["url"] not in pdf_links]
            print(f"[PDF SEARCH] PDF links từ attachment: {len(pdf_attachments)}")
            if pdf_attachments:
                for att_link in pdf_attachments:
                    print(f"[PDF SEARCH]   - {att_link['title']}: {att_link['url']}")
            
            for att_link in pdf_attachments:
                if len(file_jobs) >= self._max_file_per_page:
                    break
                file_jobs.append(self._pdf_task(ssl, att_link["title"], att_link["url"]))
                pdf_links.append(att_link["url"])
            
            # 3. Crawl các link đính kèm không phải PDF (có thể cần click để tải PDF)
            if len(file_jobs) < self._max_file_per_page:
                non_pdf_attachments = [att for att in attachment_links if not att["is_pdf"] and att["url"] not in pdf_links]
                print(f"[PDF SEARCH] Non-PDF attachment links: {len(non_pdf_attachments)}")
                if non_pdf_attachments:
                    print(f"[Attachment link] Crawl {len(non_pdf_attachments)} link đính kèm để tìm PDF...")
                    attachment_pdfs = await self._crawl_attachment_links(non_pdf_attachments, ssl)
                    print(f"[PDF SEARCH] PDF tìm thấy từ attachment crawl: {len(attachment_pdfs)}")
                    for pdf_result in attachment_pdfs:
                        if len(file_contents) >= self._max_file_per_page:
                            break
                        file_contents.append(pdf_result)
                        pdf_links.append(pdf_result.url)
            
            print(f"[PDF SEARCH] Tổng số PDF jobs: {len(file_jobs)}")
            file_results = await asyncio.gather(*file_jobs)
            for file_result in file_results:
                if file_result:
                    file_contents.append(file_result)
            print(f"[PDF SEARCH] PDF đã tải thành công: {len(file_contents)}/{len(file_jobs)}")
            
            # 4. Nếu vẫn chưa có PDF, crawl các link keyword
            if not pdf_links:
                keyword_links = self._find_keyword_links(html_result["html"], html_result["url"])
                print(f"[PDF SEARCH] Keyword links tìm thấy: {len(keyword_links)}")
                if keyword_links:
                    print(f"[Keyword link crawl] Không tìm thấy PDF trực tiếp, crawl {len(keyword_links)} link liên quan...")
                    keyword_pdfs = await self._crawl_keyword_links(keyword_links, ssl)
                    print(f"[PDF SEARCH] PDF tìm thấy từ keyword crawl: {len(keyword_pdfs)}")
                    for pdf_result in keyword_pdfs:
                        if pdf_result:
                            file_contents.append(pdf_result)
                            pdf_links.append(pdf_result["file_url"])
            
            print(f"[PDF SEARCH] Kết quả cuối cùng: {len(pdf_links)} PDF links, {len(file_contents)} PDF files đã tải\n")
        
        # Format output
        crawl_date = datetime.now().strftime("%Y-%m-%d")
        parts = [
            "---",
            f"source_url: {html_result['url']}",
            f"crawl_date: {crawl_date}",
            f"page_title: {html_result['title']}",
            f"content_type: html",
            f"has_pdf: {len(pdf_links) > 0}",
        ]
        if pdf_links:
            parts.append("pdf_links:")
            parts.extend(f" - {link}" for link in pdf_links)
        parts.append("---")
        parts.append(main_content.strip() or "> Không có nội dung HTML được trích xuất.")
        
        # PDF sections
        for file_result in file_contents:
            if file_result["text"].strip():
                filename = file_result["file_url"].split("/")[-1] or "document.pdf"
                parts.extend(["", "---", f"# PDF Extracted ({filename})", "", file_result["text"].strip(), ""])
        
        final_text = re.sub(r'\n{3,}', '\n\n', "\n".join(parts)).strip()
        
        web_source: WebSource = {
            "query": html_result["query"],
            "title": html_result["title"],
            "url": html_result["url"],
            "description": html_result["description"],
            "text": final_text,
            "files": file_contents,
            "score": html_result["score"]
        }
        if len(web_source["text"].strip()) != 0 or len(file_contents) != 0:
            print(f"[CRAWL] {web_source['url'][:60]}... | {len(main_content)} chars | {len(file_contents)} PDFs")
            return web_source
        else:
            print(f"{web_source['url']} is empty")
                
    async def _pdf_task(self, ssl: bool, title: str, url: str) -> FileSource | None:
        """Download PDF - không dùng ScrapingBee, dùng aiohttp thông thường với User-Agent"""
        async with self._semaphore:
            try:
                # Headers để download PDF (không dùng ScrapingBee)
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Accept": "application/pdf,application/octet-stream,*/*",
                    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
                }
                async with self.session.get(url=url, timeout=self.timeout, ssl=ssl, headers=headers) as response:
                    if response.ok:
                        # Kiểm tra content-type
                        content_type = response.headers.get("Content-Type", "").lower()
                        if "pdf" not in content_type and not url.endswith(".pdf"):
                            print(f"[CRAWL PDF] Warning: URL không phải PDF (Content-Type: {content_type})")
                        
                        stream = await response.content.read()
                        if not stream:
                            print(f"[CRAWL PDF] Empty response từ {url}")
                            return None
                        
                        text = self.pdf_to_text.extract_text(stream)
                        result: FileSource = {
                            "file_title": title,
                            "file_url": url,
                            "file_type": "pdf",
                            "text": text
                        }
                        print(f"[CRAWL PDF] ✓ {title[:50]}... ({len(text)} chars)")
                        return result
                    else:
                        print(f"[CRAWL PDF] Error {response.status}: {url}")
            except asyncio.TimeoutError:
                print(f"[CRAWL PDF] Timeout: {url}")
            except Exception as e:
                print(f"[CRAWL PDF] Error: {url} - {str(e)[:100]}")
            return None