from typing import Optional
from fastapi import APIRouter, Depends
from app.models.user import User
from app.schemas.agent import AgentChatRequest, AgentChatResponse, AgentSuggestionResponse
from app.services.agent_service import process_chat
from app.middleware.auth_middleware import get_current_user_optional

router = APIRouter(prefix="/agent", tags=["AI Travel Agent"])

@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(req: AgentChatRequest, user: Optional[User] = Depends(get_current_user_optional)):
    user_id = str(user.id) if user else req.sessionId or "anonymous_guest"
    history = req.chatHistory or req.history or []
    result = await process_chat(req.message, history, user_id=user_id)
    reply_text = result.get("response") or result.get("reply") or ""
    return {
        "success": True,
        "reply": reply_text,
        "response": reply_text,
        "action": result.get("action"),
        "suggestedQueries": result.get("suggestedQueries", []),
        "memories": result.get("memories", [])
    }

@router.post("/clear")
async def clear_chat_memory():
    return {
        "success": True,
        "message": "Chat session cleared."
    }

@router.get("/suggestions", response_model=AgentSuggestionResponse)
async def get_suggestions():
    return {
        "suggestions": [
            "Find luxury villas with private pools",
            "Cozy mountain cabins in Manali",
            "Best weekend getaways near Mumbai",
            "Affordable beachside stays in Goa"
        ]
    }
