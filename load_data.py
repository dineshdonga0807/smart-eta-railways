import csv
import sqlite3
import re
import shutil
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "raw" / "indian_railway_delay_data_.csv"
if not CSV_PATH.exists():
    CSV_PATH = DATA_DIR / "indian_railway_delay_data_.csv"

DB_PATH = DATA_DIR / "delays.db"

print(f"Loading data from: {CSV_PATH}")
print(f"Target SQLite database: {DB_PATH}")


def parse_delay(delay_str, sc_time=None, act_time=None):
    if not delay_str:
        return 0, "00:00:00"
    s = str(delay_str).strip()

    # Standard HH:MM:SS
    m = re.match(r"^(\d+):(\d+):(\d+)$", s)
    if m:
        hrs, mins, secs = int(m.group(1)), int(m.group(2)), int(m.group(3))
        total_mins = hrs * 60 + mins + round(secs / 60)
        return total_mins, s

    # Excel artifact (e.g. '20-01-1900 00:20')
    time_part = re.search(r"(\d+):(\d+)(?::(\d+))?$", s)
    if time_part and sc_time and act_time:
        try:
            sc_h, sc_m, _ = map(int, sc_time.split(":"))
            act_h, act_m, _ = map(int, act_time.split(":"))
            diff = (act_h * 60 + act_m) - (sc_h * 60 + sc_m)
            if diff < 0:
                diff += 24 * 60
            h = diff // 60
            m = diff % 60
            cleaned_hms = f"{h:02d}:{m:02d}:00"
            return diff, cleaned_hms
        except Exception:
            pass

    hrs = int(time_part.group(1)) if time_part else 0
    mins = int(time_part.group(2)) if time_part else 0
    return hrs * 60 + mins, f"{hrs:02d}:{mins:02d}:00"


# Connect to SQLite
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Read CSV
with open(CSV_PATH, mode="r", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    headers = [col.strip() for col in next(reader)]
    raw_rows = [row for row in reader if any(field.strip() for field in row)]

# Rename Dealy_min in header to delay_hms, and add delay_minutes_total
delay_idx = headers.index("Dealy_min") if "Dealy_min" in headers else -1
sc_idx = headers.index("Sc_arr__time") if "Sc_arr__time" in headers else -1
act_idx = headers.index("Act_arr_time") if "Act_arr_time" in headers else -1

if delay_idx != -1:
    headers[delay_idx] = "delay_hms"

headers.append("delay_minutes_total")

# Process rows
processed_rows = []
for row in raw_rows:
    row_list = list(row)
    raw_delay = row_list[delay_idx] if delay_idx != -1 else ""
    sc_val = row_list[sc_idx] if sc_idx != -1 else None
    act_val = row_list[act_idx] if act_idx != -1 else None
    mins, cleaned_hms = parse_delay(raw_delay, sc_val, act_val)
    if delay_idx != -1:
        row_list[delay_idx] = cleaned_hms
    row_list.append(mins)
    processed_rows.append(row_list)

# Recreate table
cursor.execute("DROP TABLE IF EXISTS delay_records")
col_defs = ", ".join([f'"{col}" TEXT' if col != "delay_minutes_total" else f'"{col}" INTEGER' for col in headers])
cursor.execute(f"CREATE TABLE delay_records ({col_defs})")

placeholders = ", ".join(["?"] * len(headers))
cursor.executemany(f"INSERT INTO delay_records VALUES ({placeholders})", processed_rows)
conn.commit()
conn.close()

# Keep root copy synchronized
shutil.copy2(DB_PATH, BASE_DIR / "delays.db")
print(f"Successfully loaded {len(processed_rows)} rows with delay_hms and delay_minutes_total.")
