from fastapi import APIRouter
from controllers import storeController

router = APIRouter(prefix="", tags=["Store & Bookings"])

# Homes routes
router.add_api_route("", storeController.get_homes, methods=["GET"])
router.add_api_route("/", storeController.get_homes, methods=["GET"])
router.add_api_route("/index", storeController.get_homes, methods=["GET"])
router.add_api_route("/homes", storeController.get_homes, methods=["GET"])
router.add_api_route("/homes-list", storeController.get_homes, methods=["GET"])
router.add_api_route("/homes/{home_id}", storeController.get_home_details, methods=["GET"])

# Favourites routes
router.add_api_route("/favourites", storeController.get_favourites, methods=["GET"])
router.add_api_route("/favourites", storeController.post_add_favourite, methods=["POST"])
router.add_api_route("/favourites/add", storeController.post_add_favourite, methods=["POST"])
router.add_api_route("/favourites/{home_id}", storeController.post_remove_favourite, methods=["DELETE"])
router.add_api_route("/favourites/remove/{home_id}", storeController.post_remove_favourite, methods=["POST"])

# Bookings routes
router.add_api_route("/bookings", storeController.get_bookings, methods=["GET"])
router.add_api_route("/bookings", storeController.post_create_booking, methods=["POST"])
router.add_api_route("/bookings/{booking_id}/cancel", storeController.post_cancel_booking, methods=["POST"])
router.add_api_route("/bookings/{booking_id}", storeController.delete_booking, methods=["DELETE"])
