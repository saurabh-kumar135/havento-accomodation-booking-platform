from typing import List, Optional, Any, Dict
from pydantic import BaseModel

class AgentMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class AgentChatRequest(BaseModel):
    message: str
    chatHistory: Optional[List[Dict[str, Any]]] = []
    history: Optional[List[Dict[str, Any]]] = []
    sessionId: Optional[str] = None

class AgentAction(BaseModel):
    type: str  # "VIEW_HOME", "OPEN_BOOKING", "CANCEL_BOOKING", "SEARCH_HOMES"
    data: Dict[str, Any]

class AgentChatResponse(BaseModel):
    success: bool = True
    reply: str
    response: Optional[str] = None
    action: Optional[AgentAction] = None
    suggestedQueries: Optional[List[str]] = []
    memories: Optional[List[str]] = []

class AgentSuggestionResponse(BaseModel):
    suggestions: List[str]
