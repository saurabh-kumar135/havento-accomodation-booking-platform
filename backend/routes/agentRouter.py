from fastapi import APIRouter
from controllers import agentController
from schemas.agent import AgentChatResponse, AgentSuggestionResponse

router = APIRouter(prefix="/agent", tags=["AI Travel Agent"])

router.add_api_route("/chat", agentController.post_chat, methods=["POST"], response_model=AgentChatResponse)
router.add_api_route("/clear", agentController.clear_chat_memory, methods=["POST"])
router.add_api_route("/suggestions", agentController.get_suggestions, methods=["GET"], response_model=AgentSuggestionResponse)
