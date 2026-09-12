import sqlite3
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "delays.db"
MODEL_DIR = BASE_DIR / "model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# 1. Load data
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

df["season"] = df["season"].astype(str).str.strip()
df["run_frequency"] = df["run_frequency"].astype(str).str.strip()

feature_cols = ["current_delay", "historical_avg_delay_this_train", "season", "run_frequency"]
target_col = "delay_minutes_total"

X = df[feature_cols].copy()
y = df[target_col].copy()

# 2. Same 80/20 train/test split with random_state=42
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42
)

# 3. Pipeline with OneHotEncoding for categoricals
categorical_cols = ["season", "run_frequency"]
numeric_cols = ["current_delay", "historical_avg_delay_this_train"]

preprocessor = ColumnTransformer(
    transformers=[
        ("num", "passthrough", numeric_cols),
        ("cat", OneHotEncoder(drop="first", handle_unknown="ignore", sparse_output=False), categorical_cols)
    ]
)

lr_pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("regressor", LinearRegression())
])

lr_pipeline.fit(X_train, y_train)

# 4. Evaluate on test set
y_pred_lr = lr_pipeline.predict(X_test)
mae_lr = mean_absolute_error(y_test, y_pred_lr)
rmse_lr = np.sqrt(mean_squared_error(y_test, y_pred_lr))
r2_lr = r2_score(y_test, y_pred_lr)

# Load XGBoost results from metadata.json for exact comparison
with open(MODEL_DIR / "metadata.json") as f:
    xgb_meta = json.load(f)
xgb_metrics = xgb_meta["test_metrics"]

print("--- Comparison on Test Set (20 samples) ---")
print(f"Linear Regression: MAE = {mae_lr:.4f}, RMSE = {rmse_lr:.4f}, R2 = {r2_lr:.4f}")
print(f"XGBoost Regressor: MAE = {xgb_metrics['mae']:.4f}, RMSE = {xgb_metrics['rmse']:.4f}, R2 = {xgb_metrics['r2']:.4f}")

# Check if Linear Regression is better (lower MAE)
is_better = mae_lr < xgb_metrics['mae']
print(f"Does Linear Regression perform better on MAE? {is_better}")

# Save linear model
lr_model_path = MODEL_DIR / "linear_regression_model.joblib"
joblib.dump(lr_pipeline, lr_model_path)
print(f"Saved Linear Regression pipeline to: {lr_model_path}")

# Update metadata with comparison
comparison_meta = {
    "linear_regression": {
        "mae": round(float(mae_lr), 4),
        "rmse": round(float(rmse_lr), 4),
        "r2": round(float(r2_lr), 4)
    },
    "xgboost": xgb_metrics,
    "better_model": "Linear Regression" if is_better else "XGBoost"
}

with open(MODEL_DIR / "model_comparison.json", "w") as f:
    json.dump(comparison_meta, f, indent=2)

import shutil
if Path("d:/model").exists():
    shutil.copy2(lr_model_path, Path("d:/model/linear_regression_model.joblib"))
    shutil.copy2(MODEL_DIR / "model_comparison.json", Path("d:/model/model_comparison.json"))
