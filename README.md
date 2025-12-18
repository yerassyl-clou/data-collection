Final Group Project - Streaming + Batch Data Pipeline (Airflow + Kafka + SQLite)
This repository contains our final group project implementation: a complete Docker-based streaming + batch data pipeline orchestrated with Apache Airflow, using Kafka as a message broker and SQLite as a storage/analytics layer.
Data source: OpenAQ API v3 - air quality measurements (frequently updating real-world data).

Project Goal
Demonstrate the ability to:
- collect frequently updating data from a real API,
- stream raw events through Kafka,
- clean and store data to SQLite in hourly batches,
- run daily analytics on stored data,
- document the pipeline and results

Architecture Overview
DAG 1 — Continuous Ingestion (Pseudo Streaming)
Flow: API -> Producer -> Kafka (`raw_events`)  
- Runs periodically and produces new events on each execution
- Fetches new data from the OpenAQ API every run
- Sends raw JSON messages into Kafka topic

Outputs:
- Kafka topic: `raw_events`

DAG 2 — Hourly Cleaning + Storage (Batch)
Schedule: `@hourly`  
Flow: Kafka -> Cleaning -> SQLite (`events`)  
- Reads all new Kafka messages since last run
- Cleans and normalizes data (type conversion, missing fields, invalid values)
- Writes cleaned rows into SQLite database

Outputs:
- SQLite table: `events`

DAG 3 — Daily Analytics (Batch)
Schedule: `@daily`  
Flow: SQLite (`events`) -> Aggregation -> SQLite (`daily_summary`)  
- Reads cleaned data from SQLite
- Computes aggregated daily metrics
- Writes results to separate summary table

Outputs:
- SQLite table: `daily_summary`

Data Source (API)
We use OpenAQ API v3, a public and well-documented environmental data API
Why it satisfies requirements:
- Real-world data, non-random
- Frequently updating (air quality measurements update hourly or more often depending on station)
- Structured JSON
- Public, stable, documented

We fetch:
- Sensors list for location (to map parameter names)
- Latest measurements for sensors

Kafka Topic Schema

Topic: `raw_events`
Messages are raw JSON objects produced from OpenAQ responses

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

Exact structure depends on API response and enrichment fields in `job1_producer.py`

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
Database file: app.db
	-	Host path: data/app.db
	-	Inside Airflow Docker containers: /opt/airflow/data/app.db

Table: `events` (cleaned events)
Stores cleaned rows from Kafka

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
Stores daily aggregated metrics

Recommended columns:
- `date_utc` TEXT
- `parameter` TEXT
- `count_records` INTEGER
- `min_value` REAL
- `max_value` REAL
- `avg_value` REAL

The exact schema should match the SQL created/used in `job2_cleaner.py` and `job3_analytics.py`.


Airflow Metadata Database
- PostgreSQL is used only for Airflow metadata (DAG states, task status, logs metadata)
- Project data is stored in SQLite (app.db), not in PostgreSQL


Quick Start (How to run)

Prerequisites
- Python
- Docker and Docker Compose installed (Airflow, Kafka, PostgreSQL are started using Docker Compose)

1) Environment variables
Job 1 (producer) requires OpenAQ API key, and all jobs need Kafka + SQLite settings

Set (at minimum):
- `OPENAQ_API_KEY` — required
- `KAFKA_BOOTSTRAP`:
  - inside Docker: kafka:9093
  - from host: localhost:9092
- `KAFKA_TOPIC` — default: `raw_events`
- `SQLITE_PATH`:
  - local: `data/app.db`
  - in Airflow Docker: `/opt/airflow/data/app.db`

Optional:
- `OPENAQ_LOCATION_ID` — default in code: `8118`
- `POLL_SECONDS`

In Docker/Airflow, pass these variables via `docker-compose.yml` (environment section)
Locally, you can export them in terminal

2) Start the Project 

```bash
docker compose down
docker compose up -d --build
docker compose ps
docker compose run --rm airflow-init
docker compose restart airflow-webserver airflow-scheduler
```

3) Open Airflow UI

- URL: http://localhost:8080
- Username: airflow
- Password: airflow

Stop and Restart Project

Stop containers: 
```bash
docker compose stop
```

Start again:
```bash
docker compose up -d
docker compose run --rm airflow-init
docker compose restart airflow-webserver airflow-scheduler
```
