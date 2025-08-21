import sys
if sys.version_info.minor >= 12:
    from typing import TypedDict
else:
    from typing_extensions import TypedDict
from typing import Literal

SearchEngineType = Literal["google", "brave"]

class RagSource(TypedDict):
    url: str
    title: str
    text: str
class WebSource(TypedDict):
    url: str
    title: str
    description: str
    text: str
    