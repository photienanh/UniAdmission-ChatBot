from typing import Any
from .schema import RagSource

PAGE_HEADER_TEMPLATE = "**Nguồn**: [**{title}**]({url})"
FILE_HEADER_TEMPLATE = "[{title}]({url})"

class SourceFormat:
    def __init__(self) -> None:
        pass
    def __call__(self, sources: list[RagSource]) -> str:
        """Format `RagSource` to text. Input list should not be shuffled (Order by page)."""
        if len(sources) == 0: return ""
        result: list[str] = []
        main_page_url = None
        main_file_url = None
        page_buffer: list[str] = []
        file_buffer: list[str] = []
        for index, source in enumerate(sources):
            page_url = source["url"]
            if main_page_url == page_url:
                if "file_url" not in source:
                    page_buffer.append(source["text"])
                else:
                    file_url = source["file_url"]
                    if main_file_url == file_url:
                        file_buffer.append(source["text"])
                    else:
                        page_buffer.extend(file_buffer)
                        prefix = FILE_HEADER_TEMPLATE.format(
                            title=source.get("file_title", ""),
                            url=source.get("file_url", "")
                        )
                        file_buffer = [prefix, source["text"]]
                        main_file_url = file_url
            else:
                if len(file_buffer) > 0:
                    # Flush file buffer
                    page_buffer.extend(file_buffer)
                    file_buffer.clear()
                result.extend(page_buffer)
                prefix = PAGE_HEADER_TEMPLATE.format(
                    # index=str(index),
                    title=source["title"],
                    url=source["url"]
                )
                page_buffer = [prefix, source["text"]]
                main_page_url = page_url
        if len(page_buffer) > 0:
            # Flush page buffer
            result.extend(page_buffer)
            
        return "\n".join(result)
            