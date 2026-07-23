from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum


class ExplanationLevel(str, Enum):
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    document_id: Optional[str] = None
    chat_id: Optional[str] = None
    explanation_level: ExplanationLevel = ExplanationLevel.DETAILED


class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    chat_id: str
