from typing import TypedDict, Literal

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
    