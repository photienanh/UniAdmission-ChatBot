from typing import TypedDict

class APIJobInfo(TypedDict):
    model_id: str
    message: str
    sampling_params: dict