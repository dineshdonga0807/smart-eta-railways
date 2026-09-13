# Smart ETA // Indian Railways Real-Time Delay Forecasting Engine

[![Vercel Deployment](https://img.shields.io/badge/Vercel-100%25%20Serverless%20Ready-black?style=flat&logo=vercel)](https://vercel.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB?style=flat&logo=python)](https://www.python.org)
[![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn-F7931E?style=flat&logo=scikit-learn)](https://scikit-learn.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An intelligent real-time delay forecasting platform for Indian Railways trains. Powered by machine learning (Scikit-Learn linear regression pipeline), FastAPI, an SQLite historical dataset, and an operations dashboard. Built and optimized for **100% zero-configuration deployment on Vercel Serverless Functions**.

---

## 1. Project Overview & Features

### Overview
Predicting railway arrival delays accurately requires synthesizing historical schedule performance, seasonal weather variations, operational frequencies, and active en-route delay telemetry. **Smart ETA** provides both an interactive high-density operations console and a low-latency REST API capable of serving real-time delay predictions and what-if simulation scenarios.

### Core Features
- **Machine Learning Inference Engine**: Trained on historical Indian Railways operational records, considering historical train averages, seasonality (Winter, Summer, Monsoon), frequency, and real-time delay telemetry.
- **Interactive Operations Console (`/ui`)**: Dark-mode telemetry console featuring real-time route inspection, live delay simulation overrides, ETA comparison indicators, and confidence status indicators.
- **Zero-Config Vercel Serverless Architecture**: Native `@vercel/python` integration via ASGI rewrite rules, optimized for sub-second cold starts and global edge distribution.
- **Read-Only Serverless Database**: Pre-seeded SQLite database (`data/delays.db`) containing 10 major high-traffic express routes across the Indian Railways network.
- **Live Parameter Simulation**: Allows dispatchers and commuters to simulate arbitrary delay overrides (e.g. signal failures, track maintenance) and immediately recalculate downstream ETA.
- **Interactive API Documentation**: Auto-generated Swagger (`/docs`) and ReDoc (`/redoc`) API schemas.

---

## 2. System Architecture

```
 smart-eta-railways/
 │
 ├── api/
 │   └── index.py            <-- Vercel Serverless Function entrypoint (ASGI bridge)
 │
 ├── data/
 │   └── delays.db           <-- SQLite database with train profiles and historical metrics
 │
 ├── model/
 │   ├── linear_regression_model.joblib  <-- Production ML inference pipeline
 │   └── feature_columns.json            <-- Feature definitions and categorical one-hot schema
 │
 ├── static/
 │   └── index.html          <-- Self-contained Operations Console (HTML5/CSS3/Vanilla JS)
 │
 ├── main.py                 <-- FastAPI application, route handlers, and ML inference logic
 ├── vercel.json             <-- Vercel global rewrite rules and serverless routing
 ├── requirements.txt        <-- Production runtime dependencies (kept lean for serverless limits)
 ├── requirements-dev.txt    <-- Development & offline model retraining dependencies
 └── Dockerfile & compose    <-- Optional containerized local execution
```

### Key Components:
1. **Backend**: FastAPI 0.115+ handling routing, CORS validation, schema validation, and serving static assets.
2. **ML Pipeline**: Serialized `joblib` model trained on standardized historical features with real-time dynamic inference.
3. **Database Layer**: SQLite with read-only URI connection mode (`file:... ?mode=ro`) to comply with AWS Lambda / Vercel read-only root filesystems.
4. **Frontend Dashboard**: Responsive single-page application served directly from `/` and `/ui`, utilizing pure CSS variables, SVG icons, and relative API paths (zero hardcoded endpoints).

---

## 3. Local Setup & Installation

### Prerequisites
- Python 3.10 or 3.11
- Git

### Installation Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/dineshdonga0807/smart-eta-railways.git
   cd smart-eta-railways
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Windows (CMD)
   python -m venv venv
   .\venv\Scripts\activate.bat

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install production dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   *(Optional) If you plan to retrain models or use XGBoost locally:*
   ```bash
   pip install -r requirements-dev.txt
   ```

---

## 4. Environment Variables

Smart ETA is designed to run out of the box with zero required environment variables. A template is provided in [`.env.example`](.env.example):

```env
# Server Configuration (Local)
PORT=8000
HOST=0.0.0.0
ENVIRONMENT=production

# CORS Origins (Comma-separated, defaults to * if unspecified)
ALLOWED_ORIGINS=*
```

On Vercel, no environment variables need to be set for the core application to run.

---

## 5. Running Locally

### Option A: Direct Execution with Uvicorn (Recommended for Development)

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser and navigate to:
- **Operations Console**: [http://localhost:8000](http://localhost:8000) or [http://localhost:8000/ui](http://localhost:8000/ui)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### Option B: Docker & Docker Compose

To run the complete stack within an isolated Linux container:

```bash
docker-compose up --build
```

The application will bind to port 8000 on your host machine.

---

## 6. Deploying to Vercel (Step-by-Step Guide)

Smart ETA has been fully configured for automated, zero-configuration deployment on Vercel.

### Step 1: Push Code to GitHub
Ensure all changes are committed and pushed to your GitHub repository:
```bash
git add .
git commit -m "Configure 100% Vercel Serverless deployment"
git push origin main
```

### Step 2: Import into Vercel
1. Log in to your [Vercel Dashboard](https://vercel.com/dashboard).
2. Click the **"Add New..."** button and choose **"Project"**.
3. Locate `smart-eta-railways` under your GitHub account and click **"Import"**.

### Step 3: Configure Project Settings
- **Framework Preset**: Select **"Other"** (Vercel automatically detects `vercel.json` and Python functions).
- **Root Directory**: `./` (leave default).
- **Build Command**: Leave empty (no Node or custom build command needed).
- **Output Directory**: Leave empty.
- **Environment Variables**: None required.

### Step 4: Deploy
Click **"Deploy"**. Vercel will:
1. Detect Python from `requirements.txt`.
2. Build the `@vercel/python` runtime for `api/index.py`.
3. Deploy the application globally with instant SSL and custom domain support.

Your deployment will be accessible at `https://<your-project-name>.vercel.app`.

---

## 7. Vercel Configuration Details

### `vercel.json`
The repository uses a single, modern rewrite rule that routes all incoming HTTP requests to the Python serverless function:

```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/api/index.py"
    }
  ]
}
```

### `api/index.py`
Vercel serverless executes functions from the `/api` directory. `api/index.py` sets up the Python path and imports the FastAPI instance:

```python
import sys
from pathlib import Path

# Add project root to sys.path so modules and assets can be resolved
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import app  # Exposes ASGI app to Vercel
```

---

## 8. API Endpoints & Request/Response Samples

### 1. Health Check
- **Endpoint**: `GET /health`
- **Description**: Verifies service status, ML model availability, and SQLite connectivity.
- **Sample Response**:
  ```json
  {
    "status": "healthy",
    "model_loaded": true,
    "database_connected": true
  }
  ```

### 2. List Supported Trains
- **Endpoint**: `GET /api/trains`
- **Description**: Returns all 10 pre-profiled trains with default metrics.
- **Sample Response**:
  ```json
  [
    {
      "train_number": "12238",
      "train_name": "Begampura Express",
      "source": "Varanasi Jn",
      "destination": "Jammu Tawi",
      "historical_avg_delay": 42.5,
      "current_delay": 50.0,
      "season": "Winter",
      "run_frequency": "Daliy"
    }
  ]
  ```

### 3. Forecast Train Delay (Default Profile)
- **Endpoint**: `GET /eta/{train_number}`
- **Example**: `GET /eta/12238`
- **Sample Response**:
  ```json
  {
    "train_number": "12238",
    "train_name": "Begampura Express",
    "predicted_delay_minutes": 46.0,
    "model_used": "linear_regression_model.joblib",
    "features_used": {
      "current_delay": 50.0,
      "historical_avg_delay_this_train": 42.5,
      "season": "Winter",
      "run_frequency": "Daliy"
    }
  }
  ```

### 4. Forecast Train Delay with Real-Time Override
- **Endpoint**: `GET /eta/{train_number}?current_delay={minutes}`
- **Example**: `GET /eta/12238?current_delay=15`
- **Sample Response**:
  ```json
  {
    "train_number": "12238",
    "train_name": "Begampura Express",
    "predicted_delay_minutes": 38.6,
    "model_used": "linear_regression_model.joblib",
    "features_used": {
      "current_delay": 15.0,
      "historical_avg_delay_this_train": 42.5,
      "season": "Winter",
      "run_frequency": "Daliy"
    }
  }
  ```

### 5. Web Console & API Documentation
- `GET /` or `GET /ui`: Serves the Operations Console interface.
- `GET /docs`: Interactive Swagger UI.
- `GET /redoc`: ReDoc documentation.

---

## 9. Troubleshooting & Serverless Optimizations

### Serverless Bundle Size (250 MB AWS Lambda Limit)
- **Problem**: Machine learning libraries like `xgboost` or large PyTorch wheels can easily exceed the 250 MB uncompressed limit of serverless runtimes.
- **Solution**: The production runtime relies on Scikit-Learn's optimized linear regression model. `xgboost` has been moved to `requirements-dev.txt`, keeping the deployment package under 75 MB.

### Read-Only Filesystem in MicroVMs
- **Problem**: Serverless execution environments mount the deployment directory as read-only. Standard SQLite calls fail with `sqlite3.OperationalError: unable to open database file` when attempting to write temporary journal files or obtain locks.
- **Solution**: SQLite connections are opened using explicit read-only URI mode:
  ```python
  sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
  ```

### Asset Streaming & File Responses
- **Problem**: Calling `FileResponse` on serverless endpoints can result in truncated responses or file descriptor leaks.
- **Solution**: The UI HTML is read directly into memory and returned via `HTMLResponse(content=...)`, guaranteeing rapid delivery with no file-locking issues.

### Relative Path API Calls
- **Problem**: Hardcoded `http://localhost:8000` or Render URLs in client-side scripts break when deployed to staging or production domains.
- **Solution**: The frontend uses clean relative paths (`/eta/...`, `/api/trains`), adapting automatically to any domain or preview environment.

---

## 10. Removal & Deprecation of Render Configurations

This repository has been fully transitioned from Render to Vercel:
- **No `render.yaml` or `Procfile`**: All web service definitions and start commands are handled natively by Vercel's ASGI runtime.
- **No Hardcoded Domains**: Any prior references to Render domains (`onrender.com`) have been removed from frontend scripts and documentation.
- **No Idle Spin-Up Delays**: Unlike free Render tiers that spin down after 15 minutes of inactivity, Vercel Serverless Functions execute with sub-second cold starts globally.
