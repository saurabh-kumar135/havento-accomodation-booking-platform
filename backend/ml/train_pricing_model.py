"""
Dynamic Pricing Model Training Pipeline for HavenTo
Trains a Random Forest regression pipeline to predict optimal nightly rates based on:
- Location clusters
- Property category
- Guest capacity
- Review rating
- Temporal & seasonal factors (month, weekend)
- Amenities offering
"""

import os
import sys
import json

# Ensure backend root directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, mean_absolute_percentage_error

# Seed for reproducibility
np.random.seed(42)

LOCATIONS = [
    "Taharpur", "Delhi", "Goa", "Mumbai", "Bangalore",
    "Jaipur", "Manali", "Rishikesh", "Udaipur", "Shimla"
]

CATEGORIES = [
    "Trending", "Villa", "Apartment", "Cabin", "Beachfront",
    "Mountain View", "Luxury Suite", "Studio", "Heritage Home"
]

ALL_AMENITIES = [
    "WiFi", "Swimming Pool", "Air Conditioning", "Fully Equipped Kitchen",
    "Free Parking", "Gym", "Hot Tub", "Ocean View",
    "Dedicated Workspace", "Pet Friendly", "Balcony", "BBQ Grill"
]

# Baseline price index per location
LOCATION_BASE = {
    "Goa": 110.0,
    "Mumbai": 130.0,
    "Udaipur": 115.0,
    "Delhi": 95.0,
    "Bangalore": 90.0,
    "Jaipur": 85.0,
    "Manali": 80.0,
    "Shimla": 78.0,
    "Rishikesh": 70.0,
    "Taharpur": 55.0
}

# Baseline price multiplier per category
CATEGORY_MULTIPLIER = {
    "Luxury Suite": 1.6,
    "Villa": 1.5,
    "Beachfront": 1.45,
    "Heritage Home": 1.3,
    "Mountain View": 1.2,
    "Cabin": 1.1,
    "Trending": 1.0,
    "Apartment": 0.9,
    "Studio": 0.75
}

# Value add per amenity (USD/night equivalent)
AMENITY_VALUATION = {
    "Swimming Pool": 38.0,
    "Hot Tub": 28.0,
    "Ocean View": 45.0,
    "Balcony": 15.0,
    "BBQ Grill": 12.0,
    "Gym": 14.0,
    "Air Conditioning": 18.0,
    "Fully Equipped Kitchen": 16.0,
    "Dedicated Workspace": 10.0,
    "WiFi": 8.0,
    "Free Parking": 10.0,
    "Pet Friendly": 12.0
}

def generate_synthetic_market_data(n_samples: int = 6000) -> pd.DataFrame:
    """Generates realistic market transaction records for vacation rentals."""
    data = []
    
    for _ in range(n_samples):
        location = np.random.choice(LOCATIONS)
        category = np.random.choice(CATEGORIES)
        guests = int(np.clip(np.random.poisson(3) + 1, 1, 14))
        rating = round(float(np.clip(np.random.normal(4.4, 0.45), 2.5, 5.0)), 2)
        month = int(np.random.randint(1, 13))
        is_weekend = int(np.random.choice([0, 1], p=[0.71, 0.29])) # ~2 days out of 7
        
        # Select 2 to 7 random amenities
        num_amenities = np.random.randint(2, 8)
        selected_amenities = list(np.random.choice(ALL_AMENITIES, size=num_amenities, replace=False))
        amenities_str = ", ".join(selected_amenities)
        
        # Base economic calculations
        base_price = LOCATION_BASE[location] * CATEGORY_MULTIPLIER[category]
        guest_factor = 1.0 + (guests - 1) * 0.18
        
        # Seasonal factor (peak in Dec-Jan, summer mountain peak in May-Jun)
        seasonal_mult = 1.0
        if month in [12, 1]:  # Holiday season peak
            seasonal_mult = 1.30
        elif month in [5, 6] and location in ["Manali", "Shimla", "Rishikesh"]:
            seasonal_mult = 1.25
        elif month in [7, 8] and location == "Goa":  # Monsoon off-peak
            seasonal_mult = 0.82
            
        weekend_mult = 1.18 if is_weekend else 1.0
        rating_mult = 1.0 + (rating - 4.0) * 0.15
        
        amenities_add = sum(AMENITY_VALUATION.get(a, 5.0) for a in selected_amenities)
        
        # Calculate target price with realistic variance
        true_price = (base_price * guest_factor * seasonal_mult * weekend_mult * rating_mult) + amenities_add
        noise = np.random.normal(0, true_price * 0.06) # 6% market variance
        final_price = round(max(25.0, true_price + noise), 2)
        
        data.append({
            "location": location,
            "category": category,
            "guests": guests,
            "rating": rating,
            "month": month,
            "is_weekend": is_weekend,
            "amenities": amenities_str,
            "price": final_price
        })
        
    return pd.DataFrame(data)

from ml.preprocessors import split_amenities

def train_and_export_model():
    print("[1/5] Generating 10,000 synthetic market observations...")
    df = generate_synthetic_market_data(n_samples=10000)
    
    X = df.drop(columns=["price"])
    y = df["price"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("[2/5] Building feature preprocessing pipeline...")
    categorical_features = ["location", "category"]
    numeric_features = ["guests", "rating", "month", "is_weekend"]
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features),
            ("num", StandardScaler(), numeric_features),
            ("amenities", CountVectorizer(tokenizer=split_amenities,
                                         token_pattern=None, binary=True), "amenities")
        ]
    )
    
    model = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("regressor", RandomForestRegressor(n_estimators=150, max_depth=22, min_samples_split=4, random_state=42, n_jobs=-1))
    ])
    
    print("[3/5] Training Random Forest Regressor...")
    model.fit(X_train, y_train)
    
    print("[4/5] Evaluating model performance on holdout test set...")
    y_pred = model.predict(X_test)
    
    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    mape = mean_absolute_percentage_error(y_test, y_pred)
    
    print(f"       R-Squared (R2)  : {r2:.4f} (Benchmark: > 0.90)")
    print(f"       RMSE            : ${rmse:.2f}")
    print(f"       MAE             : ${mae:.2f}")
    print(f"       MAPE            : {mape * 100:.2f}%")
    
    # Export artifacts
    out_dir = os.path.join(os.path.dirname(__file__), "models")
    os.makedirs(out_dir, exist_ok=True)
    
    model_path = os.path.join(out_dir, "pricing_model.joblib")
    joblib.dump(model, model_path, compress=3)
    print(f"[5/5] Exported serialized model to: {model_path}")
    
    metadata = {
        "model_type": "RandomForestRegressor",
        "n_estimators": 120,
        "max_depth": 16,
        "metrics": {
            "r2_score": round(float(r2), 4),
            "rmse": round(float(rmse), 2),
            "mae": round(float(mae), 2),
            "mape_percent": round(float(mape * 100), 2)
        },
        "supported_locations": LOCATIONS,
        "supported_categories": CATEGORIES,
        "supported_amenities": ALL_AMENITIES,
        "location_baselines": LOCATION_BASE,
        "amenity_valuations": AMENITY_VALUATION
    }
    
    metadata_path = os.path.join(out_dir, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"      Saved metadata to: {metadata_path}")
    
    return metadata

if __name__ == "__main__":
    train_and_export_model()
