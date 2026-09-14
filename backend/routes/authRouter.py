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

# Mobile Auth Routes for HavenToApp (React Native)
router.add_api_route("/mobile/login", authController.post_mobile_login, methods=["POST"])
router.add_api_route("/mobile/signup", authController.post_mobile_signup, methods=["POST"])
router.add_api_route("/mobile/me", authController.get_mobile_me, methods=["GET"])
router.add_api_route("/mobile/logout", authController.post_mobile_logout, methods=["POST"])

# Direct aliases for /api/auth/mobile/* when router mounted under /api
router.add_api_route("/auth/mobile/login", authController.post_mobile_login, methods=["POST"])
router.add_api_route("/auth/mobile/signup", authController.post_mobile_signup, methods=["POST"])
router.add_api_route("/auth/mobile/me", authController.get_mobile_me, methods=["GET"])
router.add_api_route("/auth/mobile/logout", authController.post_mobile_logout, methods=["POST"])

