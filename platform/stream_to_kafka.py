"""
MyCola Live Kafka Streamer
Sends a continuous burst of live ERP events to Kafka topics.
Run manually or via Airflow.

Usage:
  pip install kafka-python
  python platform/stream_to_kafka.py --tps 10 --duration 60
"""
import argparse, json, random, uuid, time, logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("streamer")

def stream(bootstrap="localhost:9092", tps=5, duration=60):
    try:
        from kafka import KafkaProducer
    except ImportError:
        log.error("Install kafka-python: pip install kafka-python")
        return

    producer = KafkaProducer(
        bootstrap_servers=bootstrap,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
    )
    log.info(f"Streaming {tps} events/sec for {duration}s → {bootstrap}")

    territories = [f"TER-{i:03d}" for i in range(1, 9)]
    warehouses  = [f"WH-{i:03d}"  for i in range(1, 11)]
    skus        = [f"SKU-{i:04d}" for i in range(1, 21)]
    end = time.time() + duration
    sent = 0

    while time.time() < end:
        batch_start = time.time()
        for _ in range(tps):
            eid = str(uuid.uuid4())[:8]
            now = datetime.utcnow().isoformat()
            ter = random.choice(territories)
            wh  = random.choice(warehouses)
            sku = random.choice(skus)

            producer.send("erp.fact_sales_order", value={
                "order_id": f"ORD-{eid}", "order_timestamp": now,
                "order_date": now[:10], "territory_id": ter, "warehouse_id": wh,
                "sales_rep_id": f"REP-{random.randint(1,60):04d}",
                "customer_id": f"CUST-{random.randint(1,500):06d}",
                "order_status": random.choice(["Confirmed","Pending"]),
                "grand_total_pkr": round(random.uniform(2000, 50000), 2),
                "gst_amount_pkr": round(random.uniform(100, 5000), 2),
                "num_lines": random.randint(1, 6),
            })
            producer.send("erp.fact_clickstream_event", value={
                "event_id": f"EVT-{eid}", "event_timestamp": now,
                "event_date": now[:10], "territory_id": ter,
                "event_type": random.choice(["page_view","add_to_cart","checkout","purchase"]),
                "device_type": random.choice(["mobile","desktop","tablet"]),
                "session_id": f"SES-{random.randint(1,9999):04d}",
            })
            producer.send("erp.fact_inventory_movement", value={
                "movement_id": f"MOV-{eid}", "movement_ts": now,
                "movement_date": now[:10], "sku_id": sku, "warehouse_id": wh,
                "movement_type": random.choice(["Sale","Receipt","Transfer"]),
                "quantity": random.randint(-200, 500),
                "unit_cost_pkr": round(random.uniform(10, 200), 2),
            })
            sent += 3

        producer.flush()
        elapsed = time.time() - batch_start
        sleep = max(0, 1.0 - elapsed)
        time.sleep(sleep)
        log.info(f"Sent {sent} total events | {time.time()-end+duration:.0f}s remaining")

    producer.close()
    log.info(f"Done. Total events sent: {sent}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--bootstrap", default="localhost:9092")
    p.add_argument("--tps", type=int, default=5)
    p.add_argument("--duration", type=int, default=60)
    a = p.parse_args()
    stream(a.bootstrap, a.tps, a.duration)
