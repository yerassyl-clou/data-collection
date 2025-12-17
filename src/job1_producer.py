from typing import Dict, Any
import os
import json
import time
from datetime import datetime, timezone

import requests
from kafka import KafkaProducer

API_BASE = "https://api.openaq.org/v3"

api_key = os.getenv("OPENAQ_API_KEY")
if not api_key:
    raise SystemExit("OPENAQ_API_KEY is not set")

location_id = os.getenv("OPENAQ_LOCATION_ID", "8118")
topic = os.getenv("KAFKA_TOPIC", "raw_events")
bootstrap = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
poll_seconds = int(os.getenv("POLL_SECONDS", "60"))
run_seconds = int(os.getenv("RUN_SECONDS", "0"))

started_at = time.time()
headers = {"X-API-Key": api_key}

producer = KafkaProducer(
    bootstrap_servers=bootstrap,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

sensors_url = f"{API_BASE}/locations/{location_id}/sensors"
r = requests.get(sensors_url, headers=headers, timeout=30)

if r.status_code != 200:
    print("HTTP", r.status_code, r.text)
    raise SystemExit(1)

sensors_data = r.json()

sensor_map: Dict[int, Dict[str, Any]] = {}
for s in sensors_data.get("results", []):
    sid = s.get("id")
    p = s.get("parameter") or {}
    if sid is None:
        continue
    sensor_map[int(sid)] = {
        "parameter": p.get("name"),
        "unit": p.get("units"),
        "parameter_display": p.get("displayName"),
    }

latest_url = f"{API_BASE}/locations/{location_id}/latest"

while True:
    try:
        r = requests.get(latest_url, headers=headers, params={"limit": 100}, timeout=30)
    except Exception as e:
        print("Request error:", e)
        time.sleep(poll_seconds)
        continue

    if r.status_code != 200:
        print("HTTP", r.status_code, r.text)
        time.sleep(poll_seconds)
        continue

    data = r.json()
    fetched_at = datetime.now(timezone.utc).isoformat()

    for item in data.get("results", []):
        sid = item.get("sensorsId")
        coords = item.get("coordinates") or {}
        dt = item.get("datetime") or {}

        msg = {
            "fetched_at_utc": fetched_at,
            "location_id": item.get("locationsId"),
            "sensor_id": sid,
            "parameter": sensor_map.get(int(sid), {}).get("parameter") if sid is not None else None,
            "unit": sensor_map.get(int(sid), {}).get("unit") if sid is not None else None,
            "parameter_display": sensor_map.get(int(sid), {}).get("parameter_display") if sid is not None else None,
            "datetime_utc": dt.get("utc"),
            "datetime_local": dt.get("local"),
            "value": item.get("value"),
            "latitude": coords.get("latitude"),
            "longitude": coords.get("longitude"),
        }

        producer.send(topic, msg)

    producer.flush()
    time.sleep(poll_seconds)

    if run_seconds and (time.time() - started_at) >= run_seconds:
        print("Finished producer run_seconds =", run_seconds)
        break

producer.flush()
producer.close()
