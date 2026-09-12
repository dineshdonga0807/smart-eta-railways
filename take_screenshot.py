import subprocess
import os
import shutil
from pathlib import Path

TEMP_DIR = Path("C:/Users/SREE/AppData/Local/Temp")
SCREENSHOT_TEMP = TEMP_DIR / "smart_eta_screenshot.png"
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
    "--window-size=1280,880",
    f"--user-data-dir={PROFILE_DIR}",
    "--virtual-time-budget=6000",
    f"--screenshot={SCREENSHOT_TEMP}",
    "http://127.0.0.1:8000/ui"
]

print("Launching Edge to capture screenshot...")
res = subprocess.run(edge_cmd, capture_output=True, text=True)
print("Returncode:", res.returncode)

if SCREENSHOT_TEMP.exists() and SCREENSHOT_TEMP.stat().st_size > 0:
    print(f"Captured screenshot successfully! Size: {SCREENSHOT_TEMP.stat().st_size} bytes")
    # Copy to artifact directory
    target_artifact = ARTIFACT_DIR / "smart_eta_dashboard.png"
    shutil.copy2(SCREENSHOT_TEMP, target_artifact)
    print(f"Copied to artifact dir: {target_artifact}")
    
    # Copy to workspace
    target_ws = WORKSPACE_DIR / "smart_eta_dashboard.png"
    shutil.copy2(SCREENSHOT_TEMP, target_ws)
    print(f"Copied to workspace: {target_ws}")
else:
    print("Screenshot failed or file empty.")
    print("Stderr:", res.stderr)
