from fastapi import APIRouter
from controllers import passwordResetController

router = APIRouter(prefix="/password-reset", tags=["Password Reset"])

router.add_api_route("/request", passwordResetController.post_request_reset, methods=["POST"])
router.add_api_route("/verify-token", passwordResetController.post_verify_reset_token, methods=["POST"])
router.add_api_route("/reset", passwordResetController.post_reset_password, methods=["POST"])
