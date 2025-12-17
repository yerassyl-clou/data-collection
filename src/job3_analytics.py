import os
import sqlite3
from datetime import datetime, timezone
import pandas as pd

db_path = os.getenv("SQLITE_PATH", "data/app.db")
conn = sqlite3.connect(db_path)

conn.execute("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingested_at_utc TEXT,
    fetched_at_utc TEXT,
    location_id INTEGER,
    sensor_id INTEGER,
    parameter TEXT,
    unit TEXT,
    parameter_display TEXT,
    datetime_utc TEXT,
    datetime_local TEXT,
    value REAL,
    latitude REAL,
    longitude REAL
)
""")
conn.commit()

df = pd.read_sql_query("SELECT * FROM events", conn)

if len(df) == 0:
    print("No data in events")
    raise SystemExit(0)

df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], errors="coerce", utc=True)
df = df.dropna(subset=["datetime_utc", "value", "parameter", "unit"])

df["date_utc"] = df["datetime_utc"].dt.date

summary = df.groupby(["date_utc", "parameter", "unit"]).agg(
    measurements_count=("value", "count"),
    value_avg=("value", "mean"),
    value_min=("value", "min"),
    value_max=("value", "max")
).reset_index()

summary["created_at_utc"] = datetime.now(timezone.utc).isoformat()

conn.execute("""
CREATE TABLE IF NOT EXISTS daily_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at_utc TEXT,
    date_utc TEXT,
    parameter TEXT,
    unit TEXT,
    measurements_count INTEGER,
    value_avg REAL,
    value_min REAL,
    value_max REAL
)
""")

dates = summary["date_utc"].astype(str).unique().tolist()
for d in dates:
    conn.execute("DELETE FROM daily_summary WHERE date_utc = ?", (d,))

summary_to_save = summary[[
    "created_at_utc",
    "date_utc",
    "parameter",
    "unit",
    "measurements_count",
    "value_avg",
    "value_min",
    "value_max"
]].copy()

summary_to_save["date_utc"] = summary_to_save["date_utc"].astype(str)

summary_to_save.to_sql("daily_summary", conn, if_exists="append", index=False)

conn.commit()
conn.close()

print("Saved daily_summary rows:", len(summary_to_save))
