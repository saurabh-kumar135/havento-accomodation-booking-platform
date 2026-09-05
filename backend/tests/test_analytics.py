import pytest
from services.pricingService import predict_optimal_price

@pytest.mark.asyncio
async def test_unit_predict_optimal_price():
    rec = predict_optimal_price(
        location="Goa",
        category="Villa",
        guests=6,
        rating=4.8,
        amenities=["WiFi", "Swimming Pool", "Air Conditioning"],
        month=12,
        is_weekend=1
    )
    
    assert rec["recommended_price"] > 500.0
    assert rec["min_competitive_price"] < rec["recommended_price"]
    assert rec["max_premium_price"] > rec["recommended_price"]
    assert rec["demand_tier"] == "High Demand"
    assert len(rec["value_drivers"]) > 0

@pytest.mark.asyncio
async def test_api_predict_pricing(client):
    payload = {
        "location": "Taharpur",
        "category": "Trending",
        "guests": 3,
        "rating": 8.0,
        "amenities": ["WiFi", "Free Parking"],
        "month": 5,
        "is_weekend": 0
    }
    response = await client.post("/api/analytics/pricing/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["recommended_price"] > 500
    assert data["currency"] == "INR"
    assert "projected_occupancy_rate" in data

@pytest.mark.asyncio
async def test_api_market_overview(client):
    response = await client.get("/api/analytics/market/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Taharpur" in data["supported_markets"]
    assert "Goa" in data["supported_markets"]
    assert data["model_architecture"]["accuracy_r2"] > 0.80
