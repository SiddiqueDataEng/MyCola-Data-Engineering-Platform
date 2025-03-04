"""
OutputWriter — writes generated data to:
  - CSV  (default, chunked)
  - JSON (line-delimited NDJSON)
  - Parquet (via pyarrow)
  - Kafka (JSON serialized to topics)
"""
import os
import json
import datetime
import csv
from typing import List, Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class OutputWriter:

    def __init__(
        self,
        output_format: str,
        output_dir: str,
        kafka_bootstrap_servers: Optional[str] = None,
        kafka_topic_prefix: str = "erp",
        compress_output: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ):
        self.fmt = output_format.lower()
        self.output_dir = output_dir
        self.kafka_bootstrap = kafka_bootstrap_servers
        self.kafka_prefix = kafka_topic_prefix
        self.compress = compress_output
        self.progress_cb = progress_callback
        self._kafka_producer = None

        os.makedirs(output_dir, exist_ok=True)

        if self.fmt == "kafka":
            self._init_kafka()

    # ── Kafka ─────────────────────────────────────────────────────────

    def _init_kafka(self):
        try:
            from kafka import KafkaProducer  # type: ignore
            self._kafka_producer = KafkaProducer(
                bootstrap_servers=self.kafka_bootstrap,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )
            logger.info("Kafka producer connected to %s", self.kafka_bootstrap)
        except Exception as exc:
            logger.warning("Kafka unavailable (%s); falling back to JSON output.", exc)
            self.fmt = "json"

    def _kafka_send(self, topic: str, record: Dict):
        try:
            self._kafka_producer.send(topic, value=record)
        except Exception as exc:
            logger.error("Kafka send error: %s", exc)

    # ── Public API ────────────────────────────────────────────────────

    def write_table(
        self,
        table_name: str,
        rows: List[Dict[str, Any]],
        batch_size: int = 10_000,
    ):
        """Write a complete list of records to the configured sink."""
        if not rows:
            return
        if self.fmt == "kafka":
            topic = f"{self.kafka_prefix}.{table_name}"
            for i, row in enumerate(rows):
                self._kafka_send(topic, row)
                if self.progress_cb and i % 1000 == 0:
                    self.progress_cb(i, len(rows), table_name)
            if self._kafka_producer:
                self._kafka_producer.flush()
            return

        total = len(rows)
        for chunk_start in range(0, total, batch_size):
            chunk = rows[chunk_start: chunk_start + batch_size]
            chunk_idx = chunk_start // batch_size
            fname = self._filename(table_name, chunk_idx)
            self._write_chunk(fname, chunk)
            if self.progress_cb:
                self.progress_cb(min(chunk_start + batch_size, total), total, table_name)

    def write_single(self, table_name: str, record: Dict[str, Any]):
        """Append a single record (used in live-streaming mode)."""
        if self.fmt == "kafka":
            topic = f"{self.kafka_prefix}.{table_name}"
            self._kafka_send(topic, record)
            return
        fname = self._filename(table_name, "live")
        self._append_record(fname, record)

    # ── Internal helpers ──────────────────────────────────────────────

    def _filename(self, table_name: str, suffix) -> str:
        ext = {"csv": "csv", "json": "jsonl", "parquet": "parquet"}.get(self.fmt, "jsonl")
        name = f"{table_name}_{suffix}.{ext}"
        if self.compress and self.fmt != "parquet":
            name += ".gz"
        return os.path.join(self.output_dir, name)

    def _write_chunk(self, path: str, rows: List[Dict[str, Any]]):
        if self.fmt == "csv":
            self._write_csv(path, rows)
        elif self.fmt == "json":
            self._write_ndjson(path, rows)
        elif self.fmt == "parquet":
            self._write_parquet(path, rows)

    def _append_record(self, path: str, record: Dict[str, Any]):
        """Append a single JSON line."""
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def _write_csv(self, path: str, rows: List[Dict]):
        if not rows:
            return
        # Flatten nested dicts/lists to JSON strings for CSV compatibility
        flat_rows = [_flatten(r) for r in rows]
        fieldnames = list(flat_rows[0].keys())
        open_fn = _open_maybe_gz(path)
        with open_fn(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(flat_rows)

    def _write_ndjson(self, path: str, rows: List[Dict]):
        open_fn = _open_maybe_gz(path)
        with open_fn(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, default=str) + "\n")

    def _write_parquet(self, path: str, rows: List[Dict]):
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
            flat = [_flatten(r) for r in rows]
            table = pa.Table.from_pylist(flat)
            pq.write_table(table, path, compression="snappy")
        except ImportError:
            # Fall back to NDJSON
            path = path.replace(".parquet", ".jsonl")
            self._write_ndjson(path, rows)

    def close(self):
        if self._kafka_producer:
            self._kafka_producer.flush()
            self._kafka_producer.close()


# ── Helpers ───────────────────────────────────────────────────────────

def _flatten(record: Dict) -> Dict:
    """Recursively flatten nested dicts; serialize lists to JSON strings."""
    result = {}
    for k, v in record.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                result[f"{k}__{sub_k}"] = sub_v
        elif isinstance(v, list):
            result[k] = json.dumps(v, default=str)
        else:
            result[k] = v
    return result


def _open_maybe_gz(path: str):
    if path.endswith(".gz"):
        import gzip
        return gzip.open
    return open
