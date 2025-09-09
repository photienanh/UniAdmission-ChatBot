import os, glob, shutil
import filetype
from PIL import Image
import pymupdf4llm
import pymupdf

from ..schema import FileSource
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
        try:
            doc = pymupdf.Document(stream=stream, filetype="pdf")
            md_content = pymupdf4llm.to_markdown(doc, page_chunks=True)
            content_parts = []
            
            # Handle different content formats
            if isinstance(md_content, str):
                # Simple string content
                content_parts.append(md_content)
                
            elif isinstance(md_content, list):
                if len(md_content) > 0 and isinstance(md_content[0], dict):
                    # PyMuPDF4LLM format - list of page dictionaries
                    for page in md_content: #type:ignore
                        page_content = []
                        
                        # Add page header
                        page_content.append("")
                        
                        # Add metadata if requested and available
                        if include_metadata and 'metadata' in page:
                            metadata = page['metadata']
                            page_content.append("## Document Metadata")
                            for key, value in metadata.items():
                                if value:  # Only include non-empty values
                                    page_content.append(f"- **{key.title()}**: {value}")
                            page_content.append("")
                        
                        # Add main text content
                        if 'text' in page and page['text']:
                            page_content.append(page['text'])
                        
                        # Add table of contents if available
                        if 'toc_items' in page and page['toc_items']:
                            page_content.append("\n## Table of Contents")
                            for toc_item in page['toc_items']:
                                page_content.append(f"- {toc_item}")
                        
                        content_parts.append("\n".join(page_content))
                        
                else:
                    # List of strings
                    content_parts.extend(md_content)
            
            # Join all content with page separators
            content_str = "\n---\n".join(content_parts)
            return content_str
        
        except Exception as e:
            print(f"Lỗi khi đọc PDF với PyMuPDF: {e}")
            return ""
