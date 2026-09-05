from fastapi import APIRouter
from controllers import analyticsController

router = APIRouter(prefix="/analytics", tags=["Revenue Intelligence & ML Pricing"])

# Public & host dynamic pricing prediction
router.add_api_route(
    "/pricing/predict",
    analyticsController.post_predict_price,
    methods=["POST"],
    summary="Predict dynamic optimal nightly price via ML model"
)

# Listing specific pricing evaluation
router.add_api_route(
    "/pricing/home/{home_id}",
    analyticsController.get_home_pricing_analysis,
    methods=["GET"],
    summary="Evaluate listing price against market ML benchmark"
)

# Authenticated host revenue & marketplace intelligence
router.add_api_route(
    "/host/metrics",
    analyticsController.get_host_metrics,
    methods=["GET"],
    summary="Get host RevPAR, ADR, Occupancy, and ML revenue uplift"
)

# Macro market trends & model validation metrics
router.add_api_route(
    "/market/overview",
    analyticsController.get_market_intelligence,
    methods=["GET"],
    summary="Macro travel market metrics and ML validation report"
)
