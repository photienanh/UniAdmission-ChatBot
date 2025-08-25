from typing import Any
from langchain_text_splitters.markdown import MarkdownTextSplitter
from transformers import Qwen2TokenizerFast, AutoTokenizer


class TokenMarkdownSplitter(MarkdownTextSplitter):
    def __init__(self, **kwargs: Any) -> None:
        tokenizer_name = kwargs.pop("tokenizer_name", None)
        device = kwargs.pop("device", "cpu")
        if tokenizer_name is None:
            raise ValueError("TokenMarkdownSplitter need tokenizer_name")
        self.tokenizer: Qwen2TokenizerFast = AutoTokenizer.from_pretrained(tokenizer_name, device=device)
        kwargs["length_function"] = self.__get_length
        super().__init__(**kwargs)
    def __get_length(self, text: str) -> int:
        return len(self.tokenizer.encode(text, return_tensors=None))
