"""
MyCola Live Streaming DAG
Every 5 minutes: generates a burst of live events → sends to Kafka topics
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "mycola",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
    "email_on_failure": False,
}

with DAG(
    dag_id="mycola_kafka_live_stream",
    description="Generate live ERP events and push to Kafka",
    schedule_interval="*/5 * * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["mycola", "kafka", "streaming"],
) as dag:

    def stream_events(**ctx):
        import os, sys, json, random, uuid, logging
        from datetime import datetime as dt
        log = logging.getLogger("stream_events")
        try:
            from kafka import KafkaProducer
        except ImportError:
            log.warning("kafka-python not installed, skipping.")
            return

        bootstrap = os.getenv("KAFKA_BOOTSTRAP", "kafka:29092")
        try:
            producer = KafkaProducer(
                bootstrap_servers=bootstrap,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            )
        except Exception as e:
            log.warning(f"Kafka unavailable: {e}")
            return

        territories = [f"TER-{i:03d}" for i in range(1, 9)]
        warehouses  = [f"WH-{i:03d}"  for i in range(1, 11)]
        skus        = [f"SKU-{i:04d}" for i in range(1, 21)]
        reps        = [f"REP-{i:04d}" for i in range(1, 61)]

        n = random.randint(50, 200)
        sales_sent = inv_sent = click_sent = 0
        now = dt.utcnow()

        for _ in range(n):
            eid = str(uuid.uuid4())
            ter = random.choice(territories)
            wh  = random.choice(warehouses)
            sku = random.choice(skus)
            rep = random.choice(reps)

            # Sales order event
            producer.send("erp.fact_sales_order", value={
                "order_id":        f"ORD-LIVE-{eid[:8]}",
                "order_timestamp": now.isoformat(),
                "order_date":      now.date().isoformat(),
                "territory_id":    ter,
                "warehouse_id":    wh,
                "sales_rep_id":    rep,
                "customer_id":     f"CUST-{random.randint(1,500):06d}",
                "order_status":    random.choice(["Confirmed","Pending","Confirmed","Confirmed"]),
                "grand_total_pkr": round(random.uniform(2000, 50000), 2),
                "gst_amount_pkr":  round(random.uniform(100, 5000), 2),
                "num_lines":       random.randint(1, 8),
            })
            sales_sent += 1

            # Inventory movement event
            producer.send("erp.fact_inventory_movement", value={
                "movement_id":   f"MOV-LIVE-{eid[:8]}",
                "movement_ts":   now.isoformat(),
                "movement_date": now.date().isoformat(),
                "sku_id":        sku,
                "warehouse_id":  wh,
                "movement_type": random.choice(["Sale","Receipt","Transfer"]),
                "quantity":      random.randint(-200, 500),
                "unit_cost_pkr": round(random.uniform(10, 200), 2),
            })
            inv_sent += 1

            # Clickstream event
            producer.send("erp.fact_clickstream_event", value={
                "event_id":        f"EVT-LIVE-{eid[:8]}",
                "event_timestamp": now.isoformat(),
                "event_date":      now.date().isoformat(),
                "event_type":      random.choice(["page_view","add_to_cart","checkout","search","purchase"]),
                "territory_id":    ter,
                "device_type":     random.choice(["mobile","desktop","tablet"]),
                "session_id":      f"SES-{random.randint(1,9999):04d}",
            })
            click_sent += 1

        producer.flush()
        producer.close()
        log.info(f"Streamed {sales_sent} sales, {inv_sent} inventory, {click_sent} clickstream events")
        return {"sales": sales_sent, "inventory": inv_sent, "clickstream": click_sent}

    PythonOperator(
        task_id="stream_live_events_to_kafka",
        python_callable=stream_events,
    )
