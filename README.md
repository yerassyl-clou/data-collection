Final Group Project - Streaming + Batch Data Pipeline (Airflow + Kafka + SQLite)
This repository contains our final group project implementation: a complete streaming + batch data pipeline with Airflow DAGs, using Kafka as a message broker and SQLite as a storage/analytics layer.
Data source: OpenAQ API - air quality measurements (frequently updating real-world data).

Project Goal
Demonstrate the ability to:
- collect frequently updating data from a real API,
- stream raw events through Kafka,
- clean and store data to SQLite in hourly batches,
- run daily analytics on stored data,
- document the pipeline and results.

Architecture Overview
DAG 1 — Continuous Ingestion (Pseudo Streaming)
Flow: API -> Producer -> Kafka (`raw_events`)  
- Runs regularly and launches a long-running producer process.
- Fetches new data from API every few minutes.
- Sends raw JSON messages into Kafka topic.

Outputs:
- Kafka topic: `raw_events`

DAG 2 — Hourly Cleaning + Storage (Batch)
Schedule: `@hourly`  
Flow: Kafka -> Cleaning -> SQLite (`events`)  
- Reads all new Kafka messages since last run.
- Cleans and normalizes data (type conversion, missing fields, invalid values).
- Writes cleaned rows into SQLite database.

Outputs:
- SQLite table: `events`

DAG 3 — Daily Analytics (Batch)
Schedule: `@daily`  
Flow: SQLite (`events`) -> Aggregation -> SQLite (`daily_summary`)  
- Reads cleaned data from SQLite.
- Computes aggregated daily metrics.
- Writes results to separate summary table.

Outputs:
- SQLite table: `daily_summary`

Data Source (API)
We use OpenAQ API v3.
Why it satisfies requirements:
- Real-world data, non-random.
- Frequently updating (air quality measurements update hourly or more often depending on station).
- Structured JSON.
- Public, stable, documented.

We fetch:
- Sensors list for location (to map parameter names)
- Latest measurements for sensors

Kafka Topic Schema

Topic: `raw_events`
Messages are raw JSON objects produced from OpenAQ responses.

Example fields:
- `location_id` (int)
- `location_name` (string)
- `sensor_id` (int)
- `parameter` (string)
- `value` (float)
- `unit` (string)
- `datetime` (ISO string, UTC)
- `latitude`, `longitude` (float)
- `country`, `city` (string)
- `producer_ts` (ISO string)

Exact structure depends on API response and enrichment fields in `job1_producer.py`.

Cleaning Rules (Job 2)
During hourly batch cleaning we apply:
- Type conversion:
  - numeric fields (`value`, lat/lon, ids) -> `float/int`
  - timestamps -> ISO UTC
- Drop or skip invalid records:
  - missing `datetime` or missing `value`
  - non-numeric values
- Normalization:
  - unify parameter naming
  - ensure consistent column set for SQLite insert
- Deduplication:
  - prevent writing duplicates (based on `sensor_id + datetime` when possible)

SQLite Storage (Schema)
Database file: `app.db` (or configured path in code)

Table: `events` (cleaned events)
Stores cleaned rows from Kafka.

Columns:
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `datetime_utc` TEXT
- `location_id` INTEGER
- `location_name` TEXT
- `sensor_id` INTEGER
- `parameter` TEXT
- `value` REAL
- `unit` TEXT
- `latitude` REAL
- `longitude` REAL
- `country` TEXT
- `city` TEXT
- `inserted_at_utc` TEXT

Table: `daily_summary` (aggregated analytics)
Stores daily aggregated metrics.

Recommended columns:
- `date_utc` TEXT
- `parameter` TEXT
- `count_records` INTEGER
- `min_value` REAL
- `max_value` REAL
- `avg_value` REAL

The exact schema should match the SQL created/used in `job2_cleaner.py` and `job3_analytics.py`.


Quick Start (How to run)

Prerequisites
- Python
- Apache Airflow
- Kafka broker running (local or Docker)

1) Environment variables
Job 1 (producer) requires OpenAQ API key, and all jobs need Kafka + SQLite settings.

Set (at minimum):
- `OPENAQ_API_KEY` — required
- `KAFKA_BOOTSTRAP` — example: `localhost:9092` (local) or `kafka:9092` (Docker network)
- `KAFKA_TOPIC` — default: `raw_events`
- `SQLITE_PATH` — recommended:
  - local: `data/app.db`
  - in Airflow Docker: `/opt/airflow/data/app.db`

Optional:
- `OPENAQ_LOCATION_ID` — default in code: `8118`

In Docker/Airflow, pass these variables via `docker-compose.yml` (environment section).  
Locally, you can export them in terminal.

2) Start Kafka
If you already have Kafka running — skip this.

Create the topic:
```bash
kafka-topics --create \
  --topic raw_events \
  --bootstrap-server localhost:9092 \
  --partitions 1 \
  --replication-factor 1
