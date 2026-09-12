import sqlite3
from pathlib import Path
from typing import Optional
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "delays.db"
MODEL_PATH = BASE_DIR / "model" / "linear_regression_model.joblib"
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = STATIC_DIR / "index.html"

app = FastAPI(title="Smart ETA API", version="1.0.0")

# Enable CORS for cross-origin frontend support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directory if it exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Load trained linear regression model
if not MODEL_PATH.exists():
    raise RuntimeError(f"Model file not found at: {MODEL_PATH}")

model = joblib.load(MODEL_PATH)


def get_train_profile(train_number: str):
    """Retrieve train metadata and default feature values from SQLite database."""
    if not DB_PATH.exists():
        return None

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = """
        SELECT 
            train_no,
            train_name,
            historical_avg_delay_this_train,
            current_delay,
            delay_minutes_total as latest_actual_delay,
            season,
            run_frequency
        FROM delay_features
        WHERE train_no = ?
        ORDER BY rowid DESC
        LIMIT 1
    """
    cur.execute(query, (str(train_number).strip(),))
    row = cur.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


@app.get("/")
def read_root(request: Request):
    # If a web browser requests the root URL, serve the interactive React UI
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header and INDEX_FILE.exists():
        return FileResponse(INDEX_FILE, media_type="text/html")
    return {"status": "ok"}


@app.get("/ui", response_class=HTMLResponse)
@app.get("/app", response_class=HTMLResponse)
def get_ui():
    """Serve the Smart ETA React Single Page Application."""
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=404, detail="UI index.html not found.")
    return FileResponse(INDEX_FILE, media_type="text/html")


@app.get("/api/trains")
def list_trains():
    """Return all distinct trains with metadata for dropdown selection."""
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT 
            Train_no as train_no, 
            Train_name as train_name, 
            Source as source, 
            Destitnation as destination, 
            "Distance(Km)" as distance_km
        FROM delay_records 
        ORDER BY Train_name
    """)
    trains = [dict(r) for r in cur.fetchall()]
    conn.close()
    return trains


@app.get("/eta/{train_number}")
def get_eta(
    train_number: str,
    current_delay: Optional[float] = Query(
        None, description="Current known delay in minutes. If omitted, latest recorded delay proxy is used."
    ),
    season: Optional[str] = Query(
        None, description="Season (e.g. Winter). If omitted, default recorded season is used."
    ),
    run_frequency: Optional[str] = Query(
        None, description="Run frequency (e.g. Daliy, Weekly, Tri-Weekly). If omitted, default is used."
    )
):
    profile = get_train_profile(train_number)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Train number '{train_number}' not found in delay records database."
        )

    # Use supplied parameters or fall back to train profile defaults
    used_current_delay = (
        float(current_delay) if current_delay is not None 
        else float(profile.get("latest_actual_delay", profile.get("current_delay", 0.0)))
    )
    used_hist_avg = float(profile.get("historical_avg_delay_this_train", 0.0))
    used_season = str(season).strip() if season is not None else str(profile.get("season", "Winter")).strip()
    used_run_freq = str(run_frequency).strip() if run_frequency is not None else str(profile.get("run_frequency", "Daliy")).strip()

    # Format input DataFrame matching the pipeline preprocessor
    features_input = pd.DataFrame([{
        "current_delay": used_current_delay,
        "historical_avg_delay_this_train": used_hist_avg,
        "season": used_season,
        "run_frequency": used_run_freq
    }])

    # Predict delay using Linear Regression model
    try:
        prediction_val = float(model.predict(features_input)[0])
        # Delay cannot be negative in ETA predictions
        predicted_delay = round(max(0.0, prediction_val), 1)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Model inference failed: {str(e)}"
        )

    return {
        "train_number": train_number,
        "train_name": profile.get("train_name"),
        "predicted_delay_minutes": predicted_delay,
        "model_used": "linear_regression_model.joblib",
        "features_used": {
            "current_delay": used_current_delay,
            "historical_avg_delay_this_train": used_hist_avg,
            "season": used_season,
            "run_frequency": used_run_freq
        }
    }
