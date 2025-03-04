"""
MyCola Platform — Data Loader
Loads generated CSV/Parquet files into ClickHouse tables.

Usage:
    python load_data.py                              # Load from ./generated_data to localhost
    python load_data.py --data-dir ./generated_data --host localhost --port 9000
    python load_data.py --table fact_sales_order     # Load a single table
    python load_data.py --format parquet             # Load Parquet files instead of CSV
"""
import os
import glob
import sys
import logging
import argparse
import time
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

try:
    import pandas as pd
    from clickhouse_driver import Client
except ImportError as e:
    log.error("Missing dependency: %s", e)
    log.error("Run: pip install clickhouse-driver pandas pyarrow")
    sys.exit(1)


# Maps CSV filename prefix → ClickHouse table name + column type overrides
TABLE_CONFIG = {
    "dim_customer": {
        "table": "mart_db.dim_customer",
        "date_cols": ["created_at"],
        "bool_cols": ["is_active", "pii_flag"],
    },
    "dim_product": {
        "table": "mart_db.dim_product",
        "date_cols": ["launch_date"],
        "bool_cols": ["is_active"],
    },
    "dim_warehouse": {
        "table": "mart_db.dim_warehouse",
        "date_cols": [],
        "bool_cols": ["is_active"],
    },
    "dim_territory": {
        "table": "mart_db.dim_territory",
        "date_cols": [],
        "bool_cols": [],
    },
    "dim_time": {
        "table": "mart_db.dim_time",
        "date_cols": ["full_date"],
        "bool_cols": ["is_weekend"],
    },
    "dim_sales_rep": {
        "table": "mart_db.dim_sales_rep",
        "date_cols": ["hire_date"],
        "bool_cols": ["is_active", "pii_flag"],
    },
    "dim_supplier": {
        "table": "mart_db.dim_supplier",
        "date_cols": [],
        "bool_cols": ["is_active", "pii_flag"],
    },
    "fact_sales_order": {
        "table": "mart_db.fact_sales_order",
        "date_cols": ["order_date", "order_timestamp"],
        "bool_cols": [],
        "drop_cols": ["lines"],
    },
    "fact_sales_order_line": {
        "table": "mart_db.fact_sales_order_line",
        "date_cols": [],
        "bool_cols": [],
    },
    "fact_inventory_movement": {
        "table": "mart_db.fact_inventory_movement",
        "date_cols": ["movement_date", "movement_ts"],
        "bool_cols": ["is_reconciled"],
    },
    "fact_gl_entry": {
        "table": "mart_db.fact_gl_entry",
        "date_cols": ["transaction_date", "transaction_ts"],
        "bool_cols": ["is_reconciled"],
    },
    "fact_accounts_receivable": {
        "table": "mart_db.fact_accounts_receivable",
        "date_cols": ["invoice_date", "due_date"],
        "bool_cols": ["pii_flag"],
    },
    "fact_accounts_payable": {
        "table": "mart_db.fact_accounts_payable",
        "date_cols": ["bill_date", "due_date"],
        "bool_cols": [],
    },
    "fact_production_run": {
        "table": "mart_db.fact_production_run",
        "date_cols": ["run_date", "start_ts", "end_ts"],
        "bool_cols": [],
    },
    "fact_production_downtime": {
        "table": "mart_db.fact_production_downtime",
        "date_cols": ["downtime_date", "start_ts", "end_ts"],
        "bool_cols": ["is_planned"],
    },
    "fact_quality_inspection": {
        "table": "mart_db.fact_quality_inspection",
        "date_cols": ["inspection_date", "inspection_ts"],
        "bool_cols": [],
    },
    "fact_clickstream_event": {
        "table": "mart_db.fact_clickstream_event",
        "date_cols": ["event_timestamp", "event_date"],
        "bool_cols": ["pii_flag"],
    },
}

# Load order: dimensions first, then facts
LOAD_ORDER = [
    "dim_customer", "dim_product", "dim_warehouse", "dim_territory",
    "dim_time", "dim_sales_rep", "dim_supplier",
    "fact_sales_order", "fact_sales_order_line",
    "fact_inventory_movement",
    "fact_gl_entry", "fact_accounts_receivable", "fact_accounts_payable",
    "fact_production_run", "fact_production_downtime", "fact_quality_inspection",
    "fact_clickstream_event",
]


def clean_dataframe(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Coerce types, drop unwanted columns, fill NaNs."""
    # Drop columns not in the ClickHouse schema
    for col in config.get("drop_cols", []):
        if col in df.columns:
            df = df.drop(columns=[col])

    # Drop any extra schema-deviation columns
    known_extra = ["unexpected_field", "unexpected_key"]
    for col in known_extra:
        if col in df.columns:
            df = df.drop(columns=[col])

    # Parse date/datetime columns
    for col in config.get("date_cols", []):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Convert bool-like columns to int (True/False → 1/0)
    for col in config.get("bool_cols", []):
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).fillna(0).astype(int)

    # Replace NaN/NaT with None for ClickHouse nullable columns
    df = df.where(pd.notna(df), None)

    # Explicitly convert any remaining float NaN in object/string columns to None
    # (needed for Python 3.12+ where float NaN in string columns causes 'float has no encode')
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(lambda x: None if (isinstance(x, float) and __import__('math').isnan(x)) else x)

    return df


def load_files(
    client: Client,
    prefix: str,
    config: dict,
    data_dir: str,
    file_format: str = "csv",
    batch_size: int = 10_000,
    truncate_first: bool = False,
) -> int:
    """Load all matching files for a given table prefix. Returns total rows loaded."""
    table_name = config["table"]
    pattern = os.path.join(data_dir, f"{prefix}_*.{file_format}")
    files = sorted(glob.glob(pattern))

    if not files:
        log.warning("  ⚠ No %s files found for '%s' in %s", file_format, prefix, data_dir)
        return 0

    if truncate_first:
        client.execute(f"TRUNCATE TABLE {table_name}")
        log.info("  Truncated %s", table_name)

    total_rows = 0
    t0 = time.time()

    for fpath in files:
        fname = os.path.basename(fpath)
        try:
            if file_format == "csv":
                df = pd.read_csv(fpath, low_memory=False)
            else:
                df = pd.read_parquet(fpath)

            df = clean_dataframe(df, config)

            file_rows = 0
            for start in range(0, len(df), batch_size):
                chunk = df.iloc[start:start + batch_size]
                # Convert to list of dicts for clickhouse-driver
                records = chunk.to_dict(orient="records")
                # Fix: pandas to_dict can re-introduce float('nan') for None values
                # in object columns. clickhouse_driver tries to call .encode() on them
                # and fails. Replace all float NaN values with None in every record.
                import math
                cleaned = []
                for row in records:
                    cleaned.append({
                        k: (None if isinstance(v, float) and math.isnan(v) else v)
                        for k, v in row.items()
                    })
                client.execute(
                    f"INSERT INTO {table_name} VALUES",
                    cleaned,
                    types_check=False,
                )
                file_rows += len(records)

            total_rows += file_rows
            log.info("    ✓ %s  →  %d rows", fname, file_rows)

        except Exception as exc:
            log.error("    ✗ %s  →  ERROR: %s", fname, exc)

    elapsed = time.time() - t0
    log.info("  %s: %d total rows  (%.1fs)", table_name, total_rows, elapsed)
    return total_rows


def run_verification(client: Client):
    """Print row counts for all loaded tables."""
    log.info("")
    log.info("=" * 60)
    log.info("TABLE ROW COUNTS")
    log.info("=" * 60)
    tables_in_order = [
        c["table"] for k, c in TABLE_CONFIG.items() if k in LOAD_ORDER
    ]
    grand_total = 0
    for table in dict.fromkeys(tables_in_order):  # deduplicate while preserving order
        try:
            count = client.execute(f"SELECT count() FROM {table}")[0][0]
            log.info("  %-50s %12d", table, count)
            grand_total += count
        except Exception as exc:
            log.warning("  %-50s  ERROR: %s", table, exc)
    log.info("  %s", "-" * 65)
    log.info("  %-50s %12d", "TOTAL ROWS", grand_total)


def main():
    parser = argparse.ArgumentParser(description="Load generated data into ClickHouse")
    parser.add_argument("--host", default="localhost", help="ClickHouse host")
    parser.add_argument("--port", type=int, default=9000, help="ClickHouse TCP port")
    parser.add_argument("--data-dir", default="./generated_data", help="Directory with generated files")
    parser.add_argument("--format", default="csv", choices=["csv", "parquet"], help="Input file format")
    parser.add_argument("--table", default=None, help="Load only this table prefix (e.g. fact_sales_order)")
    parser.add_argument("--batch-size", type=int, default=10_000, help="Rows per INSERT batch")
    parser.add_argument("--truncate", action="store_true", help="Truncate tables before loading")
    args = parser.parse_args()

    # Validate data dir
    if not os.path.isdir(args.data_dir):
        log.error("Data directory not found: %s", args.data_dir)
        log.error("Generate data first: python run_data_generator.py")
        sys.exit(1)

    # Connect
    log.info("Connecting to ClickHouse at %s:%d...", args.host, args.port)
    try:
        client = Client(host=args.host, port=args.port)
        ver = client.execute("SELECT version()")[0][0]
        log.info("Connected. ClickHouse version: %s", ver)
    except Exception as exc:
        log.error("Connection failed: %s", exc)
        log.error("Make sure ClickHouse is running: C:\\mycola\\clickhouse\\start_server.cmd")
        sys.exit(1)

    # Determine which tables to load
    if args.table:
        if args.table not in TABLE_CONFIG:
            log.error("Unknown table: %s. Valid options: %s", args.table, list(TABLE_CONFIG.keys()))
            sys.exit(1)
        load_list = [args.table]
    else:
        load_list = LOAD_ORDER

    log.info("")
    log.info("Loading %d table(s) from %s...", len(load_list), args.data_dir)
    log.info("")

    grand_total = 0
    t_start = time.time()
    for prefix in load_list:
        if prefix not in TABLE_CONFIG:
            log.warning("No config for table prefix '%s', skipping.", prefix)
            continue
        config = TABLE_CONFIG[prefix]
        log.info("Loading %s → %s", prefix, config["table"])
        rows = load_files(
            client=client,
            prefix=prefix,
            config=config,
            data_dir=args.data_dir,
            file_format=args.format,
            batch_size=args.batch_size,
            truncate_first=args.truncate,
        )
        grand_total += rows

    elapsed = time.time() - t_start
    log.info("")
    log.info("=" * 60)
    log.info("LOAD COMPLETE: %d total rows in %.1fs", grand_total, elapsed)
    log.info("=" * 60)

    run_verification(client)

    log.info("")
    log.info("✓ Data is now in ClickHouse! Try:")
    log.info("  C:\\mycola\\clickhouse\\client.cmd")
    log.info("  SELECT order_date, territory_id, count(), sum(grand_total_pkr)")
    log.info("  FROM mart_db.fact_sales_order")
    log.info("  GROUP BY order_date, territory_id")
    log.info("  ORDER BY order_date DESC LIMIT 10;")


if __name__ == "__main__":
    main()
