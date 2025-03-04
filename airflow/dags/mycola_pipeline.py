"""
MyCola Daily Pipeline DAG
Runs every hour:
  1. Check ClickHouse health
  2. Run dbt transformations
  3. Validate row counts
  4. Log pipeline metrics
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import logging

log = logging.getLogger(__name__)

default_args = {
    "owner": "mycola",
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
    "email_on_failure": False,
}

with DAG(
    dag_id="mycola_hourly_pipeline",
    description="MyCola data pipeline: ClickHouse health → dbt → validation",
    schedule_interval="0 * * * *",   # every hour
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["mycola", "pipeline", "dbt"],
) as dag:

    def check_clickhouse(**ctx):
        import os
        from clickhouse_driver import Client
        host = os.getenv("CLICKHOUSE_HOST", "host.docker.internal")
        port = int(os.getenv("CLICKHOUSE_PORT", "9000"))
        ch = Client(host=host, port=port)
        ver = ch.execute("SELECT version()")[0][0]
        counts = ch.execute("""
            SELECT 'fact_sales_order' AS t, count() FROM mart_db.fact_sales_order
            UNION ALL SELECT 'fact_inventory_movement', count() FROM mart_db.fact_inventory_movement
            UNION ALL SELECT 'kafka_events', count() FROM staging_db.kafka_events
        """)
        log.info(f"ClickHouse {ver} healthy. Counts: {counts}")
        ctx["task_instance"].xcom_push("ch_version", ver)
        ctx["task_instance"].xcom_push("row_counts", str(counts))
        ch.disconnect()
        return "healthy"

    def run_dbt_models(**ctx):
        import subprocess, os
        result = subprocess.run(
            ["docker", "run", "--rm",
             "-v", "/opt/airflow/dbt_project:/dbt",
             "-v", "/opt/airflow/dbt_project/profiles.yml:/root/.dbt/profiles.yml",
             "--add-host=host.docker.internal:host-gateway",
             "mycola_dbt:latest", "run"],
            capture_output=True, text=True, timeout=300
        )
        log.info(result.stdout[-3000:])
        if result.returncode != 0:
            log.error(result.stderr)
            raise Exception(f"dbt run failed: {result.stderr[-1000:]}")
        return "dbt_ok"

    def validate_marts(**ctx):
        import os
        from clickhouse_driver import Client
        host = os.getenv("CLICKHOUSE_HOST", "host.docker.internal")
        ch = Client(host=host, port=int(os.getenv("CLICKHOUSE_PORT", "9000")))
        checks = [
            ("mart_db_mart.monthly_revenue_by_territory", 1),
            ("mart_db_mart.sales_rep_performance", 1),
            ("mart_db_mart.production_efficiency", 1),
            ("mart_db_mart.inventory_summary", 1),
        ]
        for table, min_rows in checks:
            cnt = ch.execute(f"SELECT count() FROM {table}")[0][0]
            if cnt < min_rows:
                raise ValueError(f"{table} has {cnt} rows (expected >= {min_rows})")
            log.info(f"✓ {table}: {cnt} rows")
        ch.disconnect()
        return "validated"

    def log_pipeline_metrics(**ctx):
        import os
        from clickhouse_driver import Client
        from datetime import datetime as dt
        host = os.getenv("CLICKHOUSE_HOST", "host.docker.internal")
        ch = Client(host=host, port=int(os.getenv("CLICKHOUSE_PORT", "9000")))
        ch.execute("""
            CREATE TABLE IF NOT EXISTS staging_db.pipeline_runs (
                run_at       DateTime DEFAULT now(),
                dag_id       String,
                run_id       String,
                status       String,
                duration_sec Float32
            ) ENGINE = MergeTree() ORDER BY run_at
        """)
        ch.execute("INSERT INTO staging_db.pipeline_runs VALUES", [{
            "run_at":        dt.utcnow(),
            "dag_id":        ctx["dag"].dag_id,
            "run_id":        ctx["run_id"],
            "status":        "success",
            "duration_sec":  0,
        }])
        log.info("Pipeline metrics logged.")
        ch.disconnect()

    # ── Tasks ──────────────────────────────────────────────────────────
    t1 = PythonOperator(
        task_id="check_clickhouse_health",
        python_callable=check_clickhouse,
    )
    t2 = PythonOperator(
        task_id="run_dbt_transformations",
        python_callable=run_dbt_models,
    )
    t3 = PythonOperator(
        task_id="validate_mart_tables",
        python_callable=validate_marts,
    )
    t4 = PythonOperator(
        task_id="log_pipeline_metrics",
        python_callable=log_pipeline_metrics,
        trigger_rule="all_done",
    )

    t1 >> t2 >> t3 >> t4
