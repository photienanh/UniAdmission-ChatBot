from .keyword import *
from .page_rerank import *
from .reader import *
from .template import *
from .router import *

import re
JSON_PATTERN = re.compile(r"```json\s*(.*?)```", re.DOTALL)
JSON_PATTERN_2 = re.compile(r"```json\s*(.*?)", re.DOTALL)
def extract_json(text: str):
    match = re.search(JSON_PATTERN, text)
    if match:
        text = match[0]
        text = text.replace("```", "")
        text = text[4:]
        return text.strip()
    match = re.search(JSON_PATTERN, text)
    if match:
        text = match[0]
        text = text.replace("```", "")
        text = text[4:]
        return text.strip()
    return text
    