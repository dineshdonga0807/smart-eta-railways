import sqlite3
import json
import os
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "delays.db"
MODEL_DIR = BASE_DIR / "model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# 1. Load data from SQLite delay_features table
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("""
    SELECT 
        current_delay,
        historical_avg_delay_this_train,
        season,
        run_frequency,
        delay_minutes_total
    FROM delay_features
""", conn)
conn.close()

# Clean categorical text
df["season"] = df["season"].astype(str).str.strip()
df["run_frequency"] = df["run_frequency"].astype(str).str.strip()

feature_cols = ["current_delay", "historical_avg_delay_this_train", "season", "run_frequency"]
target_col = "delay_minutes_total"

X = df[feature_cols].copy()
y = df[target_col].copy()

# Convert season and run_frequency to pandas categorical dtype for XGBoost native categorical support
for col in ["season", "run_frequency"]:
    X[col] = X[col].astype("category")

# 2. 80/20 train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42
)

print(f"Dataset shape: {df.shape}")
print(f"Training set: {X_train.shape[0]} rows")
print(f"Test set:     {X_test.shape[0]} rows")

# 3. Train XGBoost Regressor
model = xgb.XGBRegressor(
    n_estimators=100,
    learning_rate=0.08,
    max_depth=4,
    enable_categorical=True,
    random_state=42
)

model.fit(X_train, y_train)

# 4. Evaluate on test set
y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print(f"\nModel Evaluation on Test Set (20 samples):")
print(f"  MAE:  {mae:.2f} minutes")
print(f"  RMSE: {rmse:.2f} minutes")
print(f"  R2:   {r2:.4f}")

# 5. Save model and metadata to /model
model_file_joblib = MODEL_DIR / "delay_xgb_model.joblib"
model_file_json = MODEL_DIR / "delay_xgb_model.json"

joblib.dump(model, model_file_joblib)
model.save_model(model_file_json)

# Save metadata
categories = {
    "season": list(X["season"].cat.categories),
    "run_frequency": list(X["run_frequency"].cat.categories)
}

metadata = {
    "model_type": "XGBRegressor",
    "features": feature_cols,
    "categorical_features": ["season", "run_frequency"],
    "categories": categories,
    "target": target_col,
    "train_rows": int(X_train.shape[0]),
    "test_rows": int(X_test.shape[0]),
    "test_metrics": {
        "mae": round(float(mae), 4),
        "rmse": round(float(rmse), 4),
        "r2": round(float(r2), 4)
    }
}

with open(MODEL_DIR / "metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)

print(f"\nModel successfully saved to:")
print(f"  - {model_file_joblib}")
print(f"  - {model_file_json}")
print(f"  - {MODEL_DIR / 'metadata.json'}")
