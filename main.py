import hashlib
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Optional
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Determine project base directory (robust for both local and Vercel serverless environments)
BASE_DIR = Path(__file__).resolve().parent
if not (BASE_DIR / "data").exists() and (BASE_DIR.parent / "data").exists():
    BASE_DIR = BASE_DIR.parent

DB_PATH = BASE_DIR / "data" / "delays.db"
MODEL_PATH = BASE_DIR / "model" / "linear_regression_model.joblib"
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = STATIC_DIR / "index.html"

app = FastAPI(
    title="Smart ETA API",
    description="Real-Time Indian Railways Delay Forecasting Engine",
    version="1.0.0"
)

# Enable GZip compression for responses > 500 bytes (Core Web Vitals & TTFB optimization)
app.add_middleware(GZipMiddleware, minimum_size=500)

# Enable CORS for cross-origin frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directory if present
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Load trained linear regression model
if not MODEL_PATH.exists():
    raise RuntimeError(f"Model file not found at: {MODEL_PATH}")

model = joblib.load(MODEL_PATH)

# In-memory caches for zero-latency serverless responses
_INDEX_HTML_CACHE: Optional[str] = None
_INDEX_HTML_ETAG: Optional[str] = None
_TRAINS_CACHE: Optional[list] = None
_DEFAULT_ETA_CACHE: dict[str, dict] = {}


def get_cached_index_html() -> tuple[str, str]:
    """Retrieve pre-cached HTML content and SHA-256 ETag to eliminate disk I/O."""
    global _INDEX_HTML_CACHE, _INDEX_HTML_ETAG
    if _INDEX_HTML_CACHE is None and INDEX_FILE.exists():
        _INDEX_HTML_CACHE = INDEX_FILE.read_text(encoding="utf-8")
        _INDEX_HTML_ETAG = f'"{hashlib.sha256(_INDEX_HTML_CACHE.encode("utf-8")).hexdigest()[:16]}"'
    return _INDEX_HTML_CACHE or "", _INDEX_HTML_ETAG or ""


def create_html_response(request: Request) -> Response:
    """Serve HTML with conditional GET 304 Not Modified and Edge cache headers."""
    content, etag = get_cached_index_html()
    if not content:
        raise HTTPException(status_code=404, detail="UI index.html not found.")

    client_etag = request.headers.get("if-none-match")
    cache_headers = {
        "ETag": etag,
        "Cache-Control": "public, max-age=0, s-maxage=3600, stale-while-revalidate=86400"
    }

    if client_etag and client_etag.strip() == etag:
        return Response(status_code=304, headers=cache_headers)

    return HTMLResponse(content=content, status_code=200, headers=cache_headers)


def get_db_connection():
    """Create a SQLite connection using read-only URI mode for serverless read-only filesystems."""
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{DB_PATH.resolve().as_posix()}?mode=ro", uri=True)
    except Exception:
        conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@lru_cache(maxsize=64)
def get_train_profile(train_number: str):
    """Retrieve train metadata and default feature values with LRU memory caching."""
    conn = get_db_connection()
    if not conn:
        return None

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


def get_trains_data():
    """Load and cache distinct train registry records in memory."""
    global _TRAINS_CACHE
    if _TRAINS_CACHE is not None:
        return _TRAINS_CACHE

    conn = get_db_connection()
    if not conn:
        return []

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
    _TRAINS_CACHE = [dict(r) for r in cur.fetchall()]
    conn.close()
    return _TRAINS_CACHE


def _compute_prediction(current_delay: float, hist_avg: float, season: str, run_freq: str) -> float:
    """Run model inference on feature inputs."""
    features_input = pd.DataFrame([{
        "current_delay": current_delay,
        "historical_avg_delay_this_train": hist_avg,
        "season": season,
        "run_frequency": run_freq
    }])
    pred_val = float(model.predict(features_input)[0])
    return round(max(0.0, pred_val), 1)


# Pre-warm default predictions for all registered trains at startup
def _warmup_cache():
    trains = get_trains_data()
    for t in trains:
        t_no = str(t.get("train_no", "")).strip()
        prof = get_train_profile(t_no)
        if prof:
            curr = float(prof.get("latest_actual_delay", prof.get("current_delay", 0.0)))
            hist = float(prof.get("historical_avg_delay_this_train", 0.0))
            seas = str(prof.get("season", "Winter")).strip()
            freq = str(prof.get("run_frequency", "Daliy")).strip()
            pred = _compute_prediction(curr, hist, seas, freq)
            _DEFAULT_ETA_CACHE[t_no] = {
                "train_number": t_no,
                "train_name": prof.get("train_name"),
                "predicted_delay_minutes": pred,
                "model_used": "linear_regression_model.joblib",
                "features_used": {
                    "current_delay": curr,
                    "historical_avg_delay_this_train": hist,
                    "season": seas,
                    "run_frequency": freq
                }
            }

try:
    _warmup_cache()
    get_cached_index_html()
except Exception:
    pass


@app.get("/")
def read_root(request: Request):
    """Serve UI if HTML requested, otherwise JSON health status."""
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header and INDEX_FILE.exists():
        return create_html_response(request)
    return JSONResponse(
        content={"status": "ok", "service": "Smart ETA API", "version": "1.0.0"},
        headers={"Cache-Control": "public, max-age=60, s-maxage=300"}
    )


@app.get("/health")
def health_check():
    """Health check endpoint for container and uptime monitoring."""
    return JSONResponse(
        content={"status": "healthy", "model_loaded": model is not None, "database_connected": DB_PATH.exists()},
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )


@app.get("/ui", response_class=HTMLResponse)
@app.get("/app", response_class=HTMLResponse)
def get_ui(request: Request):
    """Serve the Smart ETA Operations Console from RAM cache."""
    return create_html_response(request)


@app.get("/api/trains")
def list_trains():
    """Return all distinct trains with metadata (Edge cached)."""
    trains = get_trains_data()
    return JSONResponse(
        content=trains,
        headers={
            "Cache-Control": "public, max-age=3600, s-maxage=86400, stale-while-revalidate=604800"
        }
    )


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
    train_no_str = str(train_number).strip()

    # Fast-path: return pre-warmed default forecast if no overrides are provided
    if current_delay is None and season is None and run_frequency is None:
        if train_no_str in _DEFAULT_ETA_CACHE:
            return JSONResponse(
                content=_DEFAULT_ETA_CACHE[train_no_str],
                headers={"Cache-Control": "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"}
            )

    profile = get_train_profile(train_no_str)
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

    try:
        predicted_delay = _compute_prediction(used_current_delay, used_hist_avg, used_season, used_run_freq)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Model inference failed: {str(e)}"
        )

    response_data = {
        "train_number": train_no_str,
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

    return JSONResponse(
        content=response_data,
        headers={"Cache-Control": "public, max-age=60, s-maxage=300, stale-while-revalidate=3600"}
    )
