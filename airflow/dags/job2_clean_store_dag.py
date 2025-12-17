import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="job2_clean_store_dag",
    start_date=pendulum.datetime(2025, 12, 1, tz="UTC"),
    schedule="@hourly",                     
    catchup=False,
    max_active_runs=1,
    tags=["project"],
) as dag:
    clean_store = BashOperator(
        task_id="clean_kafka_to_sqlite",
        bash_command="python3 /opt/airflow/src/job2_cleaner.py",
    )
