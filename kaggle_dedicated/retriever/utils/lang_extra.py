from typing import Any
from langchain_text_splitters.markdown import MarkdownTextSplitter
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
        kwargs["length_function"] = self.__get_length
        super().__init__(**kwargs)
    def __get_length(self, text: str) -> int:
        if isinstance(self.tokenizer, tiktoken.Encoding):
            return len(self.tokenizer.encode(text))
        else:
            return len(self.tokenizer.encode(text, return_tensors=None))
