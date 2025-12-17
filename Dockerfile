FROM apache/airflow:2.8.4

USER root
RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*
USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
