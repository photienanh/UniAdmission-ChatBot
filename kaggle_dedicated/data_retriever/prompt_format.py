from typing import Any
from .schema import RagSource

PAGE_HEADER_TEMPLATE = "**Nguồn**: [**{title}**]({url})"
FILE_HEADER_TEMPLATE = "**Tài liệu**: [{title}]({url})"
CHUNK_SEPARATOR = "\n---\n"

class SourceFormat:
    def __init__(self, use_separators: bool = True) -> None:
        """
        Format RagSource to text for LLM context.
        
        Args:
            use_separators: If True, add clear separators between chunks from different sources
        """
        self.use_separators = use_separators
    
    def __call__(self, sources: list[RagSource]) -> str:
        """Format `RagSource` to text. Input list should not be shuffled (Order by page)."""
        if len(sources) == 0: 
            return ""
        
        result: list[str] = []
        main_page_url = None
        main_file_url = None
        page_buffer: list[str] = []
        file_buffer: list[str] = []
        
        for index, source in enumerate(sources):
            page_url = source["url"]
            
            if main_page_url == page_url:
                if "file_url" not in source:
                    # Page content chunk
                    page_buffer.append(source["text"])
                else:
                    # File content chunk
                    file_url = source["file_url"]
                    if main_file_url == file_url:
                        file_buffer.append(source["text"])
                    else:
                        # New file, flush previous file
                        if file_buffer:
                            page_buffer.extend(file_buffer)
                            if self.use_separators:
                                page_buffer.append("")
                        prefix = FILE_HEADER_TEMPLATE.format(
                            title=source.get("file_title", ""),
                            url=source.get("file_url", "")
                        )
                        file_buffer = [prefix, source["text"]]
                        main_file_url = file_url
            else:
                # New page, flush previous page
                if file_buffer:
                    page_buffer.extend(file_buffer)
                    file_buffer.clear()
                    if self.use_separators:
                        page_buffer.append("")
                
                if page_buffer:
                    result.extend(page_buffer)
                    if self.use_separators and index < len(sources) - 1:
                        result.append(CHUNK_SEPARATOR)
                
                prefix = PAGE_HEADER_TEMPLATE.format(
                    title=source["title"],
                    url=source["url"]
                )
                page_buffer = [prefix, source["text"]]
                main_page_url = page_url
                main_file_url = None
        
        # Flush remaining buffers
        if file_buffer:
            page_buffer.extend(file_buffer)
        
        if page_buffer:
            result.extend(page_buffer)
        
        # Join with appropriate spacing
        formatted = "\n\n".join(result)
        
        # Normalize excessive newlines (max 2 consecutive)
        import re
        formatted = re.sub(r'\n{3,}', '\n\n', formatted)
        
        return formatted
            