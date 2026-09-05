from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PricingPredictionRequest(BaseModel):
    location: str = Field(..., json_schema_extra={"example": "Goa"})
    category: str = Field(..., json_schema_extra={"example": "Villa"})
    guests: Optional[int] = Field(2, ge=1, le=20, json_schema_extra={"example": 4})
    rating: Optional[float] = Field(4.5, ge=1.0, le=5.0, json_schema_extra={"example": 4.8})
    amenities: Optional[List[str]] = Field(default_factory=list, json_schema_extra={"example": ["WiFi", "Swimming Pool", "Air Conditioning"]})
    month: Optional[int] = Field(None, ge=1, le=12, json_schema_extra={"example": 12})
    is_weekend: Optional[int] = Field(None, ge=0, le=1, json_schema_extra={"example": 1})

class PricingPredictionResponse(BaseModel):
    recommended_price: float
    min_competitive_price: float
    max_premium_price: float
    currency: str = "USD"
    demand_tier: str
    projected_occupancy_rate: float
    value_drivers: List[Dict[str, Any]]
    input_summary: Dict[str, Any]
    model_confidence: Dict[str, Any]

class HostFinancialMetricsResponse(BaseModel):
    has_properties: bool
    total_properties: int
    total_bookings: int
    total_revenue: float
    currency: str = "USD"
    financial_metrics: Dict[str, Any]
    ml_optimization: Dict[str, Any]
    properties: List[Dict[str, Any]]
