from typing import Any
import re
from langchain_text_splitters.markdown import MarkdownTextSplitter, MarkdownHeaderTextSplitter
from transformers import Qwen2TokenizerFast, AutoTokenizer
import tiktoken

class TokenMarkdownSplitter(MarkdownTextSplitter):
    def __init__(self, **kwargs: Any) -> None:
        tokenizer_name: str | None = kwargs.pop("tokenizer_name", None)
        device = kwargs.pop("device", "cpu")
        if tokenizer_name is None:
            raise ValueError("TokenMarkdownSplitter need tokenizer_name")
        self.tokenizer: tiktoken.Encoding | Qwen2TokenizerFast
        if tokenizer_name.startswith("gpt"):
            self.tokenizer = tiktoken.encoding_for_model(tokenizer_name)
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name, device=device)
        headers_to_split_on = kwargs.pop(
            "headers_to_split_on",
            [("#", "H1"), ("##", "H2"), ("###", "H3"), ("####", "H4")]
        )
        kwargs["length_function"] = self.__get_length
        super().__init__(**kwargs)
        self.header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        self._bold_heading_pattern = re.compile(r"^\s*\*\*(.+?)\*\*\s*:?\s*$")
        self._table_line_pattern = re.compile(r"^\s*\|.*\|\s*$")
    def __get_length(self, text: str) -> int:
        if isinstance(self.tokenizer, tiktoken.Encoding):
            return len(self.tokenizer.encode(text))
        else:
            return len(self.tokenizer.encode(text, return_tensors=None))
    def _normalize_inline_headings(self, text: str) -> str:
        normalized_lines: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            match = self._bold_heading_pattern.match(stripped)
            if match:
                normalized_lines.append(f"#### {match.group(1).strip()}")
            else:
                normalized_lines.append(line)
        return "\n".join(normalized_lines)
    def _preserve_tables(self, text: str) -> str:
        """Preserve tables with proper spacing and markers"""
        lines = text.splitlines()
        output: list[str] = []
        table_buffer: list[str] = []
        
        def flush_table():
            if not table_buffer:
                return
            # Add blank line before table if previous line exists
            if output and output[-1].strip():
                output.append("")
            output.append("[BẢNG]")
            output.extend(table_buffer)
            output.append("")
            table_buffer.clear()
        
        for line in lines:
            if self._table_line_pattern.match(line.strip()):
                table_buffer.append(line)
            else:
                flush_table()
                output.append(line)
        
        flush_table()
        return "\n".join(output)
    def _build_section_text(self, page_content: str, metadata: dict) -> str:
        """Build section text with hierarchical context"""
        headers: list[str] = []
        for level in ["H1", "H2", "H3", "H4", "H5", "H6"]:
            value = metadata.get(level)
            if value:
                headers.append(value.strip())
        
        section_text = page_content.strip()
        
        # If we have headers, add them as context
        if headers:
            # Use appropriate heading level based on depth
            header_depth = len(headers)
            heading_markers = "#" * min(header_depth + 2, 6)  # H3 to H6
            header_line = " > ".join(headers)
            
            if section_text:
                # Add context header before content
                return f"{heading_markers} {header_line}\n\n{section_text}"
            else:
                return f"{heading_markers} {header_line}"
        
        # No headers, return content as-is
        return section_text if section_text else ""
    def split_text(self, text: str) -> list[str]:
        normalized = self._normalize_inline_headings(text)
        normalized = self._preserve_tables(normalized)
        sections = self.header_splitter.split_text(normalized)
        if not sections:
            return MarkdownTextSplitter.split_text(self, normalized)
        chunks: list[str] = []
        for section in sections:
            section_text = self._build_section_text(
                section.page_content,
                getattr(section, "metadata", {}) or {}
            )
            if not section_text.strip():
                continue
            section_chunks = MarkdownTextSplitter.split_text(self, section_text)
            chunks.extend(section_chunks)
        return chunks
