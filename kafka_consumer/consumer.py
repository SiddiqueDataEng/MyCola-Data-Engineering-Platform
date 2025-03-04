"""
MyCola Kafka → ClickHouse Consumer
Consumes all erp.* topics and inserts into ClickHouse staging tables.
Tracks offset lag and writes consumer metrics to a status table.
"""
import os, json, time, logging, threading
from datetime import datetime
from kafka import KafkaConsumer
from kafka.admin import KafkaAdminClient
from clickhouse_driver import Client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("consumer")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
CH_HOST         = os.getenv("CLICKHOUSE_HOST", "localhost")
CH_PORT         = int(os.getenv("CLICKHOUSE_PORT", "9000"))
TOPIC_PREFIX    = "erp"
BATCH_SIZE      = 500
FLUSH_INTERVAL  = 5   # seconds

# Map Kafka topic suffix → ClickHouse target table
TOPIC_TABLE_MAP = {
    "fact_sales_order":        "staging_db.kafka_sales_order",
    "fact_inventory_movement": "staging_db.kafka_inventory",
    "fact_clickstream_event":  "staging_db.kafka_clickstream",
    "fact_gl_entry":           "staging_db.kafka_gl_entry",
    "fact_production_run":     "staging_db.kafka_production",
}

DDL = """
CREATE TABLE IF NOT EXISTS staging_db.kafka_events (
    consumed_at     DateTime DEFAULT now(),
    topic           String,
    partition       Int32,
    offset          Int64,
    payload         String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(consumed_at)
ORDER BY (topic, consumed_at);

CREATE TABLE IF NOT EXISTS staging_db.consumer_lag (
    recorded_at     DateTime DEFAULT now(),
    topic           String,
    partition       Int32,
    consumer_offset Int64,
    end_offset      Int64,
    lag             Int64
) ENGINE = MergeTree()
ORDER BY (topic, recorded_at);
"""

def wait_for_kafka(bootstrap, retries=30, delay=5):
    from kafka.admin import KafkaAdminClient
    for i in range(retries):
        try:
            admin = KafkaAdminClient(bootstrap_servers=bootstrap, request_timeout_ms=5000)
            admin.list_topics()
            admin.close()
            log.info("Kafka ready.")
            return True
        except Exception as e:
            log.info(f"Waiting for Kafka ({i+1}/{retries}): {e}")
            time.sleep(delay)
    return False

def wait_for_clickhouse(host, port, retries=20, delay=5):
    for i in range(retries):
        try:
            ch = Client(host=host, port=port)
            ch.execute("SELECT 1")
            ch.disconnect()
            log.info("ClickHouse ready.")
            return True
        except Exception as e:
            log.info(f"Waiting for ClickHouse ({i+1}/{retries}): {e}")
            time.sleep(delay)
    return False

def setup_schema(ch):
    for stmt in DDL.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                ch.execute(stmt)
            except Exception as e:
                log.warning(f"DDL warning: {e}")

def lag_reporter(bootstrap, ch_host, ch_port):
    """Background thread: every 30s records consumer lag per partition."""
    while True:
        try:
            from kafka.admin import KafkaAdminClient
            from kafka import KafkaConsumer as KC
            admin = KafkaAdminClient(bootstrap_servers=bootstrap)
            topics = [t for t in admin.list_topics() if t.startswith(TOPIC_PREFIX)]
            ch = Client(host=ch_host, port=ch_port)
            for topic in topics:
                try:
                    c = KC(bootstrap_servers=bootstrap, group_id="mycola-lag-probe",
                           auto_offset_reset="latest", enable_auto_commit=False,
                           consumer_timeout_ms=2000)
                    from kafka import TopicPartition as TP
                    partitions = [TP(topic, 0)]
                    c.assign(partitions)
                    end_offsets = c.end_offsets(partitions)
                    for tp, end in end_offsets.items():
                        try:
                            pos = c.position(tp)
                        except Exception:
                            pos = 0
                        lag = max(0, end - pos)
                        ch.execute(
                            "INSERT INTO staging_db.consumer_lag VALUES",
                            [{"recorded_at": datetime.utcnow(), "topic": topic,
                              "partition": tp.partition, "consumer_offset": pos,
                              "end_offset": end, "lag": lag}]
                        )
                    c.close()
                except Exception as te:
                    log.debug(f"Lag probe for {topic}: {te}")
            ch.disconnect()
            admin.close()
        except Exception as e:
            log.warning(f"Lag reporter error: {e}")
        time.sleep(30)

def run():
    if not wait_for_kafka(KAFKA_BOOTSTRAP):
        log.error("Kafka never became available. Exiting.")
        return
    if not wait_for_clickhouse(CH_HOST, CH_PORT):
        log.error("ClickHouse never became available. Exiting.")
        return

    ch = Client(host=CH_HOST, port=CH_PORT)
    setup_schema(ch)
    log.info("Schema ready. Starting consumer…")

    # Start lag reporter in background
    t = threading.Thread(target=lag_reporter, args=(KAFKA_BOOTSTRAP, CH_HOST, CH_PORT), daemon=True)
    t.start()

    consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="mycola-consumer",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        consumer_timeout_ms=1000,
    )
    consumer.subscribe(pattern=f"^{TOPIC_PREFIX}\\.")
    log.info(f"Subscribed to pattern ^{TOPIC_PREFIX}\\.")

    buffer = []
    last_flush = time.time()

    while True:
        try:
            records = consumer.poll(timeout_ms=500, max_records=BATCH_SIZE)
            for tp, msgs in records.items():
                for msg in msgs:
                    buffer.append({
                        "consumed_at": datetime.utcnow(),
                        "topic":       msg.topic,
                        "partition":   msg.partition,
                        "offset":      msg.offset,
                        "payload":     json.dumps(msg.value, default=str),
                    })

            now = time.time()
            if buffer and (len(buffer) >= BATCH_SIZE or now - last_flush >= FLUSH_INTERVAL):
                ch.execute("INSERT INTO staging_db.kafka_events VALUES", buffer)
                log.info(f"Flushed {len(buffer)} events to ClickHouse")
                buffer.clear()
                last_flush = now

        except Exception as e:
            log.error(f"Consumer error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    run()
