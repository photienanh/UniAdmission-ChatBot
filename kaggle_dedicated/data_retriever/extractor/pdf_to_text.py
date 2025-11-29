import os, glob, shutil
import filetype
import io
import re
from PIL import Image
import pymupdf4llm
import pymupdf

from ..schema import FileSource

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    print("[PDFProcessor] Warning: pdfplumber chưa được cài, sẽ bỏ qua định dạng bảng nâng cao")


class PDFProcessor:
    def __init__(self):
        self.supported_formats = ['.pdf']
    def is_pdf_file(self, file_path: str) -> bool:
        try:
            kind = filetype.guess(file_path)
            return kind is not None and kind.extension == 'pdf'
        except:
            return file_path.lower().endswith('.pdf')

    def extract_text(self, stream: bytes, include_metadata: bool = False) -> str:        
        # 1. Ưu tiên pdfplumber để khôi phục đúng thứ tự bảng + text như code mẫu
        if HAS_PDFPLUMBER:
            try:
                plumber_text = self._extract_with_pdfplumber(stream)
                if plumber_text.strip():
                    return plumber_text.strip()
            except Exception as e:
                print(f"[PDFProcessor] Lỗi pdfplumber: {e}, fallback sang pymupdf4llm")
        
        # 2. Fallback: PyMuPDF4LLM (giữ nguyên logic cũ)
        try:
            doc = pymupdf.Document(stream=stream, filetype="pdf")
            md_content = pymupdf4llm.to_markdown(doc, page_chunks=True)
        except Exception as e:
            print(f"Lỗi khi đọc PDF với PyMuPDF: {e}")
            return ""
        
        content_parts = []
        if isinstance(md_content, str):
            content_parts.append(md_content)
        elif isinstance(md_content, list):
            if len(md_content) > 0 and isinstance(md_content[0], dict):
                for page in md_content:  # type: ignore
                    page_content = []
                    page_content.append("")
                    if include_metadata and 'metadata' in page:
                        metadata = page['metadata']
                        page_content.append("## Document Metadata")
                        for key, value in metadata.items():
                            if value:
                                page_content.append(f"- **{key.title()}**: {value}")
                        page_content.append("")
                    if 'text' in page and page['text']:
                        page_content.append(page['text'])
                    if 'toc_items' in page and page['toc_items']:
                        page_content.append("\n## Table of Contents")
                        for toc_item in page['toc_items']:
                            page_content.append(f"- {toc_item}")
                    content_parts.append("\n".join(page_content))
            else:
                content_parts.extend(md_content)
        
        return "\n---\n".join(content_parts)

    # ---------------- pdfplumber helpers ----------------
    def _extract_with_pdfplumber(self, stream: bytes) -> str:
        pdf = pdfplumber.open(io.BytesIO(stream))
        output_parts = []
        with pdf:
            for page in pdf.pages:
                page_text = self._process_pdfplumber_page(page)
                if page_text.strip():
                    output_parts.append(page_text.strip())
        return "\n".join(output_parts)
    
    def _process_pdfplumber_page(self, page: "pdfplumber.page.Page") -> str:
        table_bboxes = []
        table_blocks = []
        
        try:
            tables = page.find_tables()
        except Exception:
            tables = []
        
        for tbl in tables:
            rows = tbl.extract()
            if not rows or not rows[0]:
                continue
            md = "| " + " | ".join(self._normalize_cell(c) for c in rows[0]) + " |\n"
            md += "| " + " | ".join(["---"] * len(rows[0])) + " |\n"
            for row in rows[1:]:
                md += "| " + " | ".join(self._normalize_cell(c) for c in row) + " |\n"
            table_blocks.append({
                "y0": tbl.bbox[1],
                "y1": tbl.bbox[3],
                "content": md.rstrip()
            })
            table_bboxes.append(tbl.bbox)
        
        text_blocks = self._extract_pdfplumber_text(page, table_bboxes)
        all_blocks = table_blocks + text_blocks
        all_blocks.sort(key=lambda b: b["y0"])
        return "\n".join(block["content"] for block in all_blocks if block["content"])
    
    def _extract_pdfplumber_text(self, page: "pdfplumber.page.Page", table_bboxes) -> list:
        text_blocks = []
        raw_text = page.extract_text() or ""
        if not raw_text.strip():
            return text_blocks
        
        lines = raw_text.split("\n")
        words = page.extract_words() or []
        pointer = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            y_candidates = []
            words_in_line = stripped.split()
            idx = pointer
            for token in words_in_line:
                while idx < len(words) and words[idx]['text'] != token:
                    idx += 1
                if idx < len(words) and words[idx]['text'] == token:
                    y_candidates.append(words[idx]['top'])
                    idx += 1
            y0 = min(y_candidates) if y_candidates else 0
            pointer = idx
            if not self._is_inside_table(y0, table_bboxes):
                text_blocks.append({
                    "y0": y0,
                    "y1": y0,
                    "content": stripped
                })
        return text_blocks
    
    def _normalize_cell(self, cell):
        if cell is None:
            return ""
        return " ".join(str(cell).split())
    
    def _is_inside_table(self, y, table_bboxes):
        for (_, y0, _, y1) in table_bboxes:
            if y >= y0 and y <= y1:
                return True
        return False
