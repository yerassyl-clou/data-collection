import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="job1_ingestion_dag",
    start_date=pendulum.datetime(2025, 12, 1, tz="UTC"),
    schedule="*/10 * * * *",              
    catchup=False,
    max_active_runs=1,
    tags=["project"],
) as dag:
    produce = BashOperator(
        task_id="produce_to_kafka",
        bash_command="RUN_SECONDS=540 python3 /opt/airflow/src/job1_producer.py",              
    )
