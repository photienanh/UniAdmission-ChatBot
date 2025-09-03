import sys
if sys.version_info.minor >= 12:
    from typing import TypedDict
else:
    from typing_extensions import TypedDict
from typing import Literal, NotRequired

SearchEngineType = Literal["google", "brave"]

class RagSource(TypedDict):
    url: str
    title: str
    text: str
    file_url: NotRequired[str]
    file_title: NotRequired[str]
    file_type: NotRequired[str]

class FileSource(TypedDict):
    file_url: str
    file_title: str
    file_type: str
    text: str
    
class WebSource(TypedDict):
    url: str
    title: str
    description: str
    text: str
    files: list[FileSource]