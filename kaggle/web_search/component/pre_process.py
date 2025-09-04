from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai import MarkdownGenerationResult, DefaultMarkdownGenerator
from typing import Any, cast
from ..schema import HtmlResult, PreProcessedResult, UrlContent
import re
from bs4 import BeautifulSoup
URL_PATTERN = re.compile(r'\[(.*?)\]\((.*?)\)', re.DOTALL)
URL_PATTERN_2 = re.compile(r'(?:\*\s|\])\((.*?)\)', re.DOTALL)
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
        return True # Tempory, as there is hardly anyway to check
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
    def _clean_html(self, html: str) -> str:
        """
        Clean HTML by removing footer, header, and specific elements for UET pages
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove common footer and header elements
            for tag in soup.find_all(['footer', 'header']):
                tag.decompose()
            
            # Remove elements with common footer/header classes and IDs
            footer_header_selectors = [
                'footer', 'header',
                '.footer', '.header', '#footer', '#header',
                '.site-footer', '.site-header', '.page-footer', '.page-header',
                '.main-footer', '.main-header', '.global-footer', '.global-header',

                # nav / menu
                'nav', '.navigation', '.navbar', '.nav-bar', '.top-nav', '.main-nav', '.bottom-nav', '.section-inner',
                'ul.menu', 'li[id^="menu-item-"]',

                # sidebar / widget
                '#sidebar', '#bottom-sidebar', '.sidebar', '.widget', '.widget-inner',

                # rác meta, social
                '.item-meta.single-post-meta.content-pad',
                '.list-inline.social-light',
                '.about-author', '.simple-navigation',
                '.post-meta', '.related-posts', '.breadcrumbs', '.list-news',
                '.gallery', '.video',
            ]
            
            for selector in footer_header_selectors:
                for element in soup.select(selector):
                    element.decompose()
            for element in soup.select('li[id^="menu-item-"]'):
                element.decompose()
            for table in soup.find_all("table"):
                # Cải thiện cấu trúc table trước khi convert
                self._improve_table_structure(table)
                # chèn marker trước và sau bảng
                table.insert_before("<!--TABLE_START-->")
                table.insert_after("<!--TABLE_END-->")
            return str(soup)
            
        except Exception as e:
            print(f"Error cleaning HTML for: {e}")
            return html  # Return original HTML if cleaning fails

    def _improve_table_structure(self, table):
        """Cải thiện cấu trúc table để đảm bảo header được convert đúng"""
        try:
            # Tìm hàng đầu tiên (thường là header)
            first_row = table.find('tr')
            if first_row:
                # Kiểm tra xem có thead không
                thead = table.find('thead')
                if not thead:
                    # Tạo thead nếu chưa có
                    thead = table.new_tag('thead')
                    
                    # Di chuyển hàng đầu tiên vào thead
                    if first_row.parent.name != 'thead':
                        first_row.extract()
                        thead.append(first_row)
                        table.insert(0, thead)
                
                # Đảm bảo cells trong header là th
                header_row = thead.find('tr') if thead else first_row
                if header_row:
                    for cell in header_row.find_all(['td', 'th']):
                        if cell.name == 'td':
                            cell.name = 'th'
                
                # Đảm bảo có tbody cho các hàng còn lại
                tbody = table.find('tbody')
                if not tbody:
                    tbody = table.new_tag('tbody')
                    # Di chuyển tất cả tr còn lại vào tbody
                    for row in table.find_all('tr'):
                        if row.parent.name not in ['thead', 'tbody']:
                            row.extract()
                            tbody.append(row)
                    if tbody.find('tr'):
                        table.append(tbody)
        except Exception as e:
            pass

    def __processs_lines(self, text: str, min_length: int) -> str:
        lines = text.splitlines()
        valid_lines: list[str] = []
        for line in lines:
            line = line.strip()
            solid_line = re.sub(WHITE_SPACE, '', line)
            if (solid_line != "" and len(solid_line) > min_length) or "|" in line or "---" in line or "<!--TABLE>" in line:
                valid_lines.append(line)
        return "\n".join(valid_lines)
    def __process(self, html: str, url: str) -> str:
        # Clean HTML before processing
        cleaned_html = self._clean_html(html)
        parsed: MarkdownGenerationResult = self.generator.generate_markdown(
            input_html=cleaned_html,
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
        fit_markdown = self.__processs_lines(raw_markdown, 5) # Changed this
        result: PreProcessedResult = {
            **input,
            "extracted_content": fit_markdown,
            "ref_urls": ref_urls,
            "image_urls": image_urls,
            "pdf_urls": pdf_urls
        }
        return result
    