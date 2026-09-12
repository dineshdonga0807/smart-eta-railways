import sqlite3
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "delays.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Create delay_features table
cur.execute("DROP TABLE IF EXISTS delay_features")

create_feature_table_query = """
CREATE TABLE delay_features AS
SELECT 
    Train_id AS train_id,
    Train_no AS train_no,
    Train_name AS train_name,
    Date AS date,
    COALESCE(LAG(delay_minutes_total, 1) OVER (PARTITION BY Train_no ORDER BY rowid), 0) AS current_delay,
    ROUND(AVG(delay_minutes_total) OVER (PARTITION BY Train_no), 2) AS historical_avg_delay_this_train,
    Season AS season,
    Run_frequency AS run_frequency,
    delay_minutes_total
FROM delay_records
"""
cur.execute(create_feature_table_query)
conn.commit()

# Verify count
cur.execute("SELECT COUNT(*) FROM delay_features")
total = cur.fetchone()[0]
print(f"Total rows in delay_features: {total}")

# Fetch 10 sample rows
cur.execute("""
SELECT 
    train_id,
    train_no,
    train_name,
    current_delay,
    historical_avg_delay_this_train,
    season,
    run_frequency,
    delay_minutes_total
FROM delay_features
LIMIT 10
""")
sample_rows = cur.fetchall()
print("\nSample 10 rows:")
for r in sample_rows:
    print(r)

conn.close()

# Sync to root delays.db
shutil.copy2(DB_PATH, BASE_DIR / "delays.db")
print("\nDatabase updated and synced successfully.")
