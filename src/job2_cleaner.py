import os
import json
import sqlite3
from datetime import datetime, timezone
import pandas as pd
from kafka import KafkaConsumer

topic = os.getenv("KAFKA_TOPIC", "raw_events")
bootstrap = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
group_id = os.getenv("KAFKA_GROUP_ID", "job2_cleaner_group")
db_path = os.getenv("SQLITE_PATH", "data/app.db")

consumer = KafkaConsumer(
    topic,
    bootstrap_servers=bootstrap,
    group_id=group_id,
    auto_offset_reset="earliest",
    enable_auto_commit=False,
    value_deserializer=lambda v: json.loads(v.decode("utf-8"))
)

messages = []

empty_polls = 0
max_empty_polls = 3

while True:
    batch = consumer.poll(timeout_ms=2000)

    if not batch:
        empty_polls += 1
        if empty_polls >= max_empty_polls:
            break
        continue

    empty_polls = 0

    #collect all in to one list
    for tp, records in batch.items():
        for rec in records:
            messages.append(rec.value)

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

if len(messages) == 0:
    print("No new messages")
    consumer.close()
    conn.close()
    raise SystemExit(0)

df = pd.DataFrame(messages)

df["value"] = pd.to_numeric(df["value"], errors="coerce")
df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], errors="coerce", utc=True)

df = df.dropna(subset=["sensor_id", "parameter", "unit", "datetime_utc", "value"])
df = df[df["value"] >= 0]

df = df.drop_duplicates(subset=["sensor_id", "parameter", "datetime_utc"])

df["ingested_at_utc"] = datetime.now(timezone.utc).isoformat()

df_to_save = df[[
    "ingested_at_utc",
    "fetched_at_utc",
    "location_id",
    "sensor_id",
    "parameter",
    "unit",
    "parameter_display",
    "datetime_utc",
    "datetime_local",
    "value",
    "latitude",
    "longitude"
]].copy()

df_to_save["datetime_utc"] = df_to_save["datetime_utc"].astype(str)

df_to_save.to_sql("events", conn, if_exists="append", index=False)

conn.commit()
consumer.commit()
consumer.close()
conn.close()

print("Saved rows:", len(df_to_save))
