from typing import TypedDict, Optional, Literal

class SourceInfo(TypedDict):
    url: str
    title: str
    description: str
    content: str
    timestamp: str

class UserMessage(TypedDict):
    role: Literal["user"]
    message: str
    
class BotMessage(TypedDict):
    role: Literal["bot"]
    search_query: str
    message: str
    model_id: str
    rag_sources: list[SourceInfo]
    search_sources: list[SourceInfo]
    
class WebSearchParam(TypedDict):
    in_domain: bool
    k_pages: int
    k_docs: int
    
class ModelInput(TypedDict):
    context: list[UserMessage | BotMessage]
    model_id: str
    web_search: Optional[WebSearchParam]

class ModelOutput(ModelInput):
    # ModelInput +
    response: BotMessage

class ModelInfo(TypedDict):
    name: str
    id: str
    params_size: str
    
class JobInfo(TypedDict):
    id: str
    data: ModelInput
    
class JobResult(TypedDict):
    id: str
    success: bool
    data: ModelOutput | str

class RequestData(TypedDict):
    job_id: Optional[str]
    payload: Optional[ModelInput]
    
class ClientInfo(TypedDict):
    name: str
    uid: str
    models: list[ModelInfo]
    
class ResponseData(TypedDict):
    client: ClientInfo
    job_id: str
    payload: ModelOutput
        
class ErrorData(TypedDict):
    client: ClientInfo
    job_id: str
    error: str
