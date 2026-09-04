from fastapi import APIRouter
from controllers import emailVerificationController

router = APIRouter(prefix="/verify-email", tags=["Email Verification"])

router.add_api_route("/send-otp", emailVerificationController.post_send_otp, methods=["POST"])
router.add_api_route("/verify-otp", emailVerificationController.post_verify_otp, methods=["POST"])
router.add_api_route("/resend-otp", emailVerificationController.post_resend_otp, methods=["POST"])
