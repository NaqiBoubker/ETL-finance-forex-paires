from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import sys
import os

# Makes your project importable inside Airflow
sys.path.insert(0, '/opt/airflow/project')

from ingestion.jobs.historical_ingestion import (
    get_connection,
    ensure_table,
    get_last_date,
    fetch_data,
    safe_insert,
    SYMBOLS
)

# ── Default args ──────────────────────────────────────────
default_args = {
    'owner': 'airflow',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': False,
}

# ── Ingestion task ────────────────────────────────────────
def run_ingestion():
    conn = get_connection()
    try:
        ensure_table(conn)
        for symbol in SYMBOLS:
            clean = symbol.replace("=X", "")
            try:
                start = get_last_date(conn, clean)
                df = fetch_data(symbol, start)
                if df is not None:
                    safe_insert(conn, df, clean)
            except Exception as e:
                print(f"[ERROR] {clean}: {e}")
                continue
    finally:
        conn.close()

# ── DAG ───────────────────────────────────────────────────
with DAG(
    dag_id='daily_fx_pipeline',
    default_args=default_args,
    description='Daily FX ingestion → dbt run → dbt test',
    schedule_interval='0 6 * * 1-5',   # 6am, Mon–Fri only
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['fx', 'ingestion', 'dbt'],
) as dag:

    t1_ingest = PythonOperator(
        task_id='ingest_fx_data',
        python_callable=run_ingestion,
    )

    t2_dbt_run = BashOperator(
        task_id='dbt_run',
        bash_command='cd /opt/airflow/project/dbt/finance_project && dbt run --profiles-dir .',
    )

    t3_dbt_test = BashOperator(
        task_id='dbt_test',
        bash_command='cd /opt/airflow/project/dbt/finance_project && dbt test --profiles-dir .',
    )

    # ── Pipeline order ────────────────────────────────────
    t1_ingest >> t2_dbt_run >> t3_dbt_test