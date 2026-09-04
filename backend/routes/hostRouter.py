from fastapi import APIRouter
from controllers import hostController

router = APIRouter(prefix="/host", tags=["Host Management"])

router.add_api_route("/homes", hostController.get_host_homes, methods=["GET"])
router.add_api_route("/homes", hostController.post_add_home, methods=["POST"])
router.add_api_route("/homes/edit", hostController.post_edit_home, methods=["POST"])
router.add_api_route("/homes/{home_id}", hostController.post_edit_home, methods=["PUT"])
router.add_api_route("/homes/{home_id}", hostController.delete_home, methods=["DELETE"])
router.add_api_route("/homes/delete/{home_id}", hostController.delete_home, methods=["POST"])
router.add_api_route("/bookings", hostController.get_host_bookings, methods=["GET"])
