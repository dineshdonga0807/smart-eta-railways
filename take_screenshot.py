import subprocess
import shutil
from pathlib import Path
import time

TEMP_DIR = Path("C:/Users/SREE/AppData/Local/Temp")
SCREENSHOT_TEMP = TEMP_DIR / "smart_eta_redesign.png"
PROFILE_DIR = TEMP_DIR / "edge_headless_profile"
ARTIFACT_DIR = Path("C:/Users/SREE/.gemini/antigravity/brain/56ca8655-df56-4a57-b912-e5ba99bad0d3")
WORKSPACE_DIR = Path("d:/Smart ETA")

if SCREENSHOT_TEMP.exists():
    SCREENSHOT_TEMP.unlink()

edge_cmd = [
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--window-size=1380,960",
    f"--user-data-dir={PROFILE_DIR}",
    "--virtual-time-budget=6000",
    f"--screenshot={SCREENSHOT_TEMP}",
    "http://127.0.0.1:8000/ui"
]

print("Capturing redesigned dashboard screenshot...")
res = subprocess.run(edge_cmd, capture_output=True, text=True)
print("Return code:", res.returncode)

if SCREENSHOT_TEMP.exists() and SCREENSHOT_TEMP.stat().st_size > 0:
    print(f"Screenshot captured: {SCREENSHOT_TEMP.stat().st_size} bytes")
    shutil.copy2(SCREENSHOT_TEMP, ARTIFACT_DIR / "smart_eta_redesign.png")
    shutil.copy2(SCREENSHOT_TEMP, WORKSPACE_DIR / "smart_eta_redesign.png")
    shutil.copy2(SCREENSHOT_TEMP, ARTIFACT_DIR / "smart_eta_dashboard.png")
    shutil.copy2(SCREENSHOT_TEMP, WORKSPACE_DIR / "smart_eta_dashboard.png")
    print("Copied successfully to artifacts and workspace.")
else:
    print("Screenshot capture failed.")
    print(res.stderr)
