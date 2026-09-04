from typing import Optional
from fastapi import Depends
from models.user import User
from schemas.agent import AgentChatRequest, AgentChatResponse, AgentSuggestionResponse
from services.agentService import process_chat
from middleware.auth import get_current_user_optional

async def post_chat(req: AgentChatRequest, user: Optional[User] = Depends(get_current_user_optional)):
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

async def clear_chat_memory():
    return {
        "success": True,
        "message": "Chat session cleared."
    }

async def get_suggestions():
    return {
        "suggestions": [
            "Find luxury villas with private pools",
            "Cozy mountain cabins in Manali",
            "Best weekend getaways near Mumbai",
            "Affordable beachside stays in Goa"
        ]
    }
