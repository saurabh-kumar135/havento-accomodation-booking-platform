from fastapi import APIRouter
from controllers import authController

router = APIRouter(prefix="", tags=["Auth"])

router.add_api_route("/login", authController.get_login, methods=["GET"])
router.add_api_route("/signup", authController.get_signup, methods=["GET"])
router.add_api_route("/check-session", authController.check_session, methods=["GET"])
router.add_api_route("/signup", authController.post_signup, methods=["POST"])
router.add_api_route("/login", authController.post_login, methods=["POST"])
router.add_api_route("/google-login", authController.post_google_login, methods=["POST"])
router.add_api_route("/logout", authController.post_logout, methods=["POST"])
router.add_api_route("/change-password", authController.change_password, methods=["POST"])
