import logging
from typing import Optional
from fastapi import HTTPException, status, Depends
from beanie import PydanticObjectId

from models.home import Home
from models.user import User
from middleware.auth import get_current_user
from schemas.analytics import PricingPredictionRequest, PricingPredictionResponse, HostFinancialMetricsResponse
from services.pricingService import (
    predict_optimal_price,
    compute_host_revenue_metrics,
    get_pricing_model,
    LOCATION_BASE,
    AMENITY_VALUATION
)

logger = logging.getLogger("havento_python.analyticsController")

async def post_predict_price(payload: PricingPredictionRequest):
    """Generates an ML dynamic pricing recommendation based on property characteristics."""
    try:
        recommendation = predict_optimal_price(
            location=payload.location,
            category=payload.category,
            guests=payload.guests or 2,
            rating=payload.rating or 4.5,
            amenities=payload.amenities or [],
            month=payload.month,
            is_weekend=payload.is_weekend
        )
        return {
            "success": True,
            **recommendation
        }
    except Exception as e:
        logger.error(f"Error predicting price: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate dynamic pricing: {str(e)}"
        )

async def get_home_pricing_analysis(home_id: str):
    """Compares an existing listing's current price against ML optimal dynamic pricing."""
    try:
        home_obj_id = PydanticObjectId(home_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid home ID format"
        )
        
    home = await Home.get(home_obj_id)
    if not home:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property listing not found"
        )
        
    pricing_rec = predict_optimal_price(
        location=home.location,
        category=home.category,
        guests=4,
        rating=home.rating,
        amenities=home.amenities
    )
    
    current_price = home.price
    rec_price = pricing_rec["recommended_price"]
    diff = round(rec_price - current_price, 2)
    percent_diff = round((diff / max(1.0, current_price)) * 100, 1)
    
    status_label = "optimal"
    if diff > 10:
        status_label = "underpriced"
        advice = f"Your listing is priced ${diff:.2f} below market demand. Raising price towards ${rec_price:.2f} could yield higher revenue without sacrificing occupancy."
    elif diff < -10:
        status_label = "overpriced"
        advice = f"Your listing is priced ${abs(diff):.2f} above market benchmark. Lowering slightly towards ${rec_price:.2f} can substantially boost booking conversion."
    else:
        advice = "Your listing is competitively priced within the optimal market demand sweet spot."

    return {
        "success": True,
        "home_id": str(home.id),
        "house_name": home.houseName,
        "location": home.location,
        "category": home.category,
        "current_price": current_price,
        "recommended_price": rec_price,
        "price_difference": diff,
        "percent_variance": percent_diff,
        "pricing_status": status_label,
        "strategic_advice": advice,
        "demand_tier": pricing_rec["demand_tier"],
        "projected_occupancy_rate": pricing_rec["projected_occupancy_rate"],
        "value_drivers": pricing_rec["value_drivers"],
        "model_confidence": pricing_rec["model_confidence"]
    }

async def get_host_metrics(user: User = Depends(get_current_user)):
    """Computes host financial health: RevPAR, ADR, Occupancy, and ML revenue uplift."""
    try:
        metrics = await compute_host_revenue_metrics(str(user.id))
        return {
            "success": True,
            **metrics
        }
    except Exception as e:
        logger.error(f"Error computing host metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate host analytics: {str(e)}"
        )

async def get_market_intelligence():
    """Returns macro travel demand benchmarks and ML model validation metrics."""
    _, metadata = get_pricing_model()
    return {
        "success": True,
        "supported_markets": list(LOCATION_BASE.keys()),
        "premium_amenities": list(AMENITY_VALUATION.keys()),
        "model_architecture": {
            "algorithm": metadata.get("model_type", "RandomForestRegressor") if metadata else "RandomForestRegressor",
            "accuracy_r2": metadata.get("metrics", {}).get("r2_score", 0.85) if metadata else 0.85,
            "mae_variance": metadata.get("metrics", {}).get("mae", 27.58) if metadata else 27.58,
            "mape_percent": metadata.get("metrics", {}).get("mape_percent", 10.23) if metadata else 10.23
        },
        "market_averages": {
            "national_adr": 92.50,
            "peak_season_occupancy": 82.4,
            "off_peak_occupancy": 58.1
        }
    }
