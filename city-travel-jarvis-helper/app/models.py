from typing import Any, Literal
from pydantic import BaseModel, Field

class AttachmentRef(BaseModel):
    ref: str; name: str; mime_type: str; size_bytes: int | None = None; sha256: str | None = None
class RequestContext(BaseModel):
    user_intent: str | None = None; source_plugin_ids: list[str] = Field(default_factory=list); dry_run: bool = False
class PluginRequest(BaseModel):
    contract_version: Literal["0.1.0"] = "0.1.0"
    request_id: str = Field(min_length=4, max_length=160)
    trace_id: str | None = None
    capability: str = Field(min_length=3, max_length=120)
    locale: str = "ru-RU"; timezone: str = "Europe/Moscow"
    payload: dict[str, Any] = Field(default_factory=dict)
    attachments: list[AttachmentRef] = Field(default_factory=list, max_length=8)
    context: RequestContext = Field(default_factory=RequestContext)
class CommitRequest(BaseModel):
    contract_version: Literal["0.1.0"] = "0.1.0"
    request_id: str = Field(min_length=4, max_length=160)
    trace_id: str | None = None
    capability: str = Field(min_length=3, max_length=120)
    commit_token: str = Field(min_length=20)
    confirmed: Literal[True]
