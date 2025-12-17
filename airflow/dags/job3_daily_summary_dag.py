import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="job3_daily_summary_dag",
    start_date=pendulum.datetime(2025, 12, 1, tz="UTC"),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["project"],
) as dag:
    summary = BashOperator(
        task_id="compute_daily_summary",
        bash_command="python3 /opt/airflow/src/job3_analytics.py",
    )
