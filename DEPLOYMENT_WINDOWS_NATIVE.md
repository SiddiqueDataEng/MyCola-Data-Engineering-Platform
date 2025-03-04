# MyCola Data Platform — Windows Native Deployment Guide

**Single-Node, On-Premise, Development/Demo Stack for Windows 10/11**

---

## Hardware Profile (My system)

- **CPU**: Intel Core i3 @ 3.2 GHz (2 cores)
- **RAM**: 8 GB
- **Disk**: 240 GB free
- **OS**: Windows 10 Pro 64-bit

**Verdict**: ✅ **Sufficient** for a single-node dev/demo environment with the following adjustments:
- Reduce ClickHouse max memory to 4 GB
- Reduce Kafka heap to 512 MB
- Use lightweight alternatives where possible
- Run components sequentially instead of all-at-once if needed

---

## Architecture — Phase 1: Core Pipeline

We'll build the platform **incrementally** in working phases:

### Phase 1A: Data Ingestion → Storage (Week 1-2)

```
Data Generator → CSV/JSON Files → Python ETL Scripts → ClickHouse
```

**Components**:
- ✅ Data Generator (already built)
- ✅ ClickHouse (Windows native binary, 4 GB heap limit)
- ✅ Python ETL scripts (read CSV → insert into ClickHouse)

**Why start here**: 
- Validates the end-to-end data flow without Kafka/Airflow complexity
- Gets you a working analytical warehouse quickly
- You can start writing SQL queries and building dashboards immediately

### Phase 1B: Add Orchestration (Week 3)

```
Data Generator → Files → Airflow DAG → Python ETL → ClickHouse
```

**New component**:
- Airflow (Python package, SQLite backend for dev)

**Why add this**:
- Introduces scheduling and retry logic
- Prepares for incremental loads
- Adds observability (DAG run history, logs)

### Phase 1C: Add Transformation Layer (Week 4)

```
Data Generator → Files → Airflow → ClickHouse (staging) → dbt → ClickHouse (mart)
```

**New component**:
- dbt Core (Python package)

**Why add this**:
- SQL-first transformation (no Python ETL boilerplate)
- Built-in testing, lineage, incremental models
- Industry-standard approach

---

## Phase 2: Add Streaming (Week 5-6)

```
Data Generator → Kafka → Python Consumer → ClickHouse (staging) → dbt → Mart
```

**New components**:
- Kafka (Windows .bat scripts, 512 MB heap)
- Schema Registry (Confluent community, embedded)

**Why add this**:
- Simulates real CDC ingestion
- Tests streaming latency SLAs
- Prepares for production-like architecture

---

## Phase 3: Add BI Layer (Week 7-8)

```
ClickHouse (mart) → Apache Superset → Dashboards
```

**New component**:
- Apache Superset (Python package with SQLite backend)

**Why add this**:
- Self-service dashboards
- Row-level security testing
- Completes the full platform stack

---

## Installation Guide — Phase 1A

### Step 1: Install ClickHouse (Windows Native)

ClickHouse provides official Windows builds.

**Download**:
```powershell
# Download ClickHouse binary
Invoke-WebRequest -Uri "https://builds.clickhouse.com/master/windows/clickhouse.exe" -OutFile "C:\clickhouse\clickhouse.exe"
```

**Configure** (`C:\clickhouse\config.xml`):
```xml
<clickhouse>
    <max_server_memory_usage>4000000000</max_server_memory_usage>  <!-- 4 GB -->
    <listen_host>0.0.0.0</listen_host>
    <http_port>8123</http_port>
    <tcp_port>9000</tcp_port>
    <path>C:/clickhouse/data/</path>
    <tmp_path>C:/clickhouse/tmp/</tmp_path>
    <user_files_path>C:/clickhouse/user_files/</user_files_path>
    <format_schema_path>C:/clickhouse/format_schemas/</format_schema_path>
</clickhouse>
```

**Start**:
```powershell
cd C:\clickhouse
.\clickhouse.exe server
```

**Verify**:
```powershell
# In another terminal
.\clickhouse.exe client
# You should see the ClickHouse prompt
```

### Step 2: Create Database Schema

Create a SQL script `F:\siddi\clickstream_sales_analytics\clickhouse_schema.sql`:

```sql
-- ClickHouse Schema for MyCola Data Warehouse

-- Staging database (raw data landing zone)
CREATE DATABASE IF NOT EXISTS staging_db;

-- Mart database (final analytical tables)
CREATE DATABASE IF NOT EXISTS mart_db;

-- ═══════════════════════════════════════════════════════════════
-- Dimension Tables (mart_db)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mart_db.dim_customer
(
    customer_id         String,
    customer_name       String,
    contact_name        Nullable(String),
    phone               Nullable(String),
    email               Nullable(String),
    address             String,
    city                String,
    territory_id        String,
    territory_name      String,
    channel_type        String,
    credit_limit_pkr    UInt32,
    credit_terms_days   UInt16,
    is_active           UInt8,
    created_at          DateTime,
    pii_flag            UInt8
)
ENGINE = MergeTree()
ORDER BY customer_id;

CREATE TABLE IF NOT EXISTS mart_db.dim_product
(
    sku_id            String,
    sku_name          String,
    category          String,
    size_ml           UInt16,
    unit_price_pkr    Float32,
    cost_price_pkr    Float32,
    units_per_case    UInt16,
    is_active         UInt8,
    launch_date       Date,
    tax_rate_pct      Float32
)
ENGINE = MergeTree()
ORDER BY sku_id;

CREATE TABLE IF NOT EXISTS mart_db.dim_warehouse
(
    warehouse_id      String,
    warehouse_name    String,
    territory_id      String,
    capacity_units    UInt32,
    is_active         UInt8
)
ENGINE = MergeTree()
ORDER BY warehouse_id;

CREATE TABLE IF NOT EXISTS mart_db.dim_territory
(
    territory_id      String,
    territory_name    String,
    region            String,
    country           String
)
ENGINE = MergeTree()
ORDER BY territory_id;

CREATE TABLE IF NOT EXISTS mart_db.dim_time
(
    date_id           String,
    full_date         Date,
    year              UInt16,
    quarter           UInt8,
    month             UInt8,
    month_name        String,
    week_of_year      UInt8,
    day_of_week       UInt8,
    day_name          String,
    is_weekend        UInt8,
    fiscal_year       UInt16,
    fiscal_quarter    UInt8
)
ENGINE = MergeTree()
ORDER BY date_id;

CREATE TABLE IF NOT EXISTS mart_db.dim_sales_rep
(
    rep_id                String,
    rep_name              String,
    email                 Nullable(String),
    phone                 Nullable(String),
    territory_id          String,
    hire_date             Date,
    is_active             UInt8,
    monthly_target_pkr    UInt32,
    pii_flag              UInt8
)
ENGINE = MergeTree()
ORDER BY rep_id;

CREATE TABLE IF NOT EXISTS mart_db.dim_supplier
(
    supplier_id           String,
    supplier_name         String,
    contact_name          String,
    phone                 String,
    email                 Nullable(String),
    city                  String,
    country               String,
    material_category     String,
    payment_terms_days    UInt16,
    is_active             UInt8,
    pii_flag              UInt8
)
ENGINE = MergeTree()
ORDER BY supplier_id;

-- ═══════════════════════════════════════════════════════════════
-- Fact Tables (mart_db)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mart_db.fact_sales_order
(
    order_id            String,
    order_date          Date,
    order_timestamp     DateTime,
    customer_id         Nullable(String),
    customer_name       String,
    sales_rep_id        String,
    rep_name            String,
    territory_id        String,
    warehouse_id        String,
    order_status        String,
    num_lines           UInt16,
    total_amount_pkr    Float32,
    gst_amount_pkr      Float32,
    grand_total_pkr     Float32,
    payment_terms_days  UInt16
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(order_date)
ORDER BY (territory_id, order_date, order_id);

CREATE TABLE IF NOT EXISTS mart_db.fact_sales_order_line
(
    order_line_id       String,
    order_id            String,
    line_number         UInt16,
    sku_id              String,
    sku_name            String,
    quantity            UInt32,
    unit_price_pkr      Float32,
    discount_pct        Float32,
    line_total_pkr      Float32,
    warehouse_id        String
)
ENGINE = MergeTree()
ORDER BY (order_id, line_number);

CREATE TABLE IF NOT EXISTS mart_db.fact_inventory_movement
(
    movement_id         String,
    movement_date       Date,
    movement_ts         DateTime,
    sku_id              String,
    sku_name            String,
    warehouse_id        String,
    movement_type       String,
    quantity            Int32,
    closing_stock       Int32,
    unit_cost_pkr       Float32,
    total_cost_pkr      Float32,
    supplier_id         Nullable(String),
    reference_doc       String,
    is_reconciled       UInt8
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(movement_date)
ORDER BY (warehouse_id, sku_id, movement_date);

CREATE TABLE IF NOT EXISTS mart_db.fact_gl_entry
(
    transaction_id      String,
    transaction_date    Date,
    transaction_ts      DateTime,
    fiscal_year         UInt16,
    fiscal_period       String,
    account_id          String,
    account_name        String,
    account_type        String,
    entry_type          String,
    amount_pkr          Float32,
    cost_centre         String,
    reference_number    String,
    description         Nullable(String),
    posted_by           Nullable(String),
    is_reconciled       UInt8,
    currency            String,
    exchange_rate       Float32
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(transaction_date)
ORDER BY (account_id, transaction_date, transaction_id);

CREATE TABLE IF NOT EXISTS mart_db.fact_production_run
(
    run_id              String,
    run_date            Date,
    line_id             String,
    line_name           String,
    sku_id              String,
    sku_name            String,
    shift               String,
    start_ts            DateTime,
    end_ts              DateTime,
    run_hours           Float32,
    planned_units       UInt32,
    actual_units        UInt32,
    defective_units     UInt32,
    good_units          UInt32,
    efficiency_pct      Float32,
    defect_rate_pct     Float32,
    oee_pct             Float32,
    operator_id         Nullable(String),
    batch_number        String
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(run_date)
ORDER BY (line_id, run_date, run_id);

CREATE TABLE IF NOT EXISTS mart_db.fact_clickstream_event
(
    event_id            String,
    event_timestamp     DateTime,
    event_date          Date,
    session_id          String,
    customer_id         Nullable(String),
    territory_id        String,
    event_type          String,
    page_url            String,
    sku_id              Nullable(String),
    order_id            Nullable(String),
    device_type         String,
    os                  String,
    browser             String,
    ip_address          Nullable(String),
    utm_source          Nullable(String),
    utm_medium          Nullable(String),
    utm_campaign        Nullable(String),
    time_on_page_sec    Nullable(UInt16),
    search_query        Nullable(String),
    pii_flag            UInt8
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, session_id, event_timestamp);

-- ═══════════════════════════════════════════════════════════════
-- Example Materialized View (Pre-Aggregation)
-- ═══════════════════════════════════════════════════════════════

CREATE MATERIALIZED VIEW IF NOT EXISTS mart_db.mv_daily_sales_summary
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(order_date)
ORDER BY (territory_id, order_date)
AS
SELECT
    order_date,
    territory_id,
    count() AS num_orders,
    sum(grand_total_pkr) AS total_revenue_pkr,
    sum(gst_amount_pkr) AS total_gst_pkr
FROM mart_db.fact_sales_order
GROUP BY order_date, territory_id;
```

**Apply schema**:
```powershell
Get-Content F:\siddi\clickstream_sales_analytics\clickhouse_schema.sql | .\clickhouse.exe client --multiquery
```

### Step 3: Load Data into ClickHouse

Create a Python loader script `F:\siddi\clickstream_sales_analytics\load_data_to_clickhouse.py`:

```python
"""
Load generated CSV data into ClickHouse.
"""
import os
import glob
import pandas as pd
from clickhouse_driver import Client

CLICKHOUSE_HOST = "localhost"
CLICKHOUSE_PORT = 9000
DATA_DIR = "./generated_data"

# Table mapping: CSV prefix → ClickHouse table
TABLE_MAP = {
    "dim_customer": "mart_db.dim_customer",
    "dim_product": "mart_db.dim_product",
    "dim_warehouse": "mart_db.dim_warehouse",
    "dim_territory": "mart_db.dim_territory",
    "dim_time": "mart_db.dim_time",
    "dim_sales_rep": "mart_db.dim_sales_rep",
    "dim_supplier": "mart_db.dim_supplier",
    "fact_sales_order": "mart_db.fact_sales_order",
    "fact_sales_order_line": "mart_db.fact_sales_order_line",
    "fact_inventory_movement": "mart_db.fact_inventory_movement",
    "fact_gl_entry": "mart_db.fact_gl_entry",
    "fact_production_run": "mart_db.fact_production_run",
    "fact_clickstream_event": "mart_db.fact_clickstream_event",
}

def load_table(client: Client, csv_pattern: str, table_name: str):
    files = glob.glob(os.path.join(DATA_DIR, csv_pattern))
    if not files:
        print(f"⚠ No files found for {csv_pattern}")
        return
    
    total_rows = 0
    for csv_file in files:
        df = pd.read_csv(csv_file, low_memory=False)
        # Convert bool to int for ClickHouse compatibility
        for col in df.columns:
            if df[col].dtype == 'bool':
                df[col] = df[col].astype(int)
        
        # Insert in chunks
        batch_size = 10_000
        for start in range(0, len(df), batch_size):
            chunk = df.iloc[start:start + batch_size]
            client.insert_dataframe(f"INSERT INTO {table_name} VALUES", chunk)
            total_rows += len(chunk)
        
        print(f"  ✓ Loaded {os.path.basename(csv_file)}: {len(df):,} rows")
    
    print(f"✓ {table_name}: {total_rows:,} total rows")

def main():
    client = Client(host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT)
    
    print("Loading data into ClickHouse...")
    print()
    
    for prefix, table in TABLE_MAP.items():
        print(f"Loading {table}...")
        load_table(client, f"{prefix}_*.csv", table)
        print()
    
    # Verify row counts
    print("Final row counts:")
    for table in set(TABLE_MAP.values()):
        count = client.execute(f"SELECT count() FROM {table}")[0][0]
        print(f"  {table}: {count:,} rows")
    
    print()
    print("✓ Data load complete!")

if __name__ == "__main__":
    main()
```

**Install ClickHouse driver**:
```powershell
pip install clickhouse-driver pandas
```

**Run loader**:
```powershell
python load_data_to_clickhouse.py
```

### Step 4: Query Your Data!

```powershell
.\clickhouse.exe client
```

**Example queries**:
```sql
-- Daily sales by territory
SELECT 
    order_date,
    territory_id,
    count() AS num_orders,
    sum(grand_total_pkr) AS revenue_pkr
FROM mart_db.fact_sales_order
GROUP BY order_date, territory_id
ORDER BY order_date DESC, revenue_pkr DESC
LIMIT 20;

-- Top 10 products by revenue
SELECT 
    l.sku_id,
    p.sku_name,
    sum(l.line_total_pkr) AS total_revenue_pkr,
    sum(l.quantity) AS total_units_sold
FROM mart_db.fact_sales_order_line l
LEFT JOIN mart_db.dim_product p ON l.sku_id = p.sku_id
GROUP BY l.sku_id, p.sku_name
ORDER BY total_revenue_pkr DESC
LIMIT 10;

-- Production efficiency by line
SELECT 
    line_id,
    line_name,
    count() AS num_runs,
    avg(efficiency_pct) AS avg_efficiency,
    avg(oee_pct) AS avg_oee,
    sum(good_units) AS total_good_units
FROM mart_db.fact_production_run
GROUP BY line_id, line_name
ORDER BY avg_oee DESC;

-- Check materialized view performance
SELECT * FROM mart_db.mv_daily_sales_summary
ORDER BY order_date DESC, total_revenue_pkr DESC
LIMIT 20;
```

---

## Phase 1B: Add Airflow (Next Steps)

Once Phase 1A is working, install Airflow:

```powershell
pip install apache-airflow==2.8.0
airflow db init
airflow users create --username admin --firstname Admin --lastname User --role Admin --email admin@mycola.local
airflow webserver --port 8080   # Terminal 1
airflow scheduler                # Terminal 2
```

Then migrate your loader script into an Airflow DAG for scheduled/incremental loads.

---

## Memory Management Tips

With 8 GB RAM, here's how to avoid crashes:

| Component | Memory Limit | Config |
|---|---|---|
| ClickHouse | 4 GB | `<max_server_memory_usage>4000000000</max_server_memory_usage>` |
| Airflow | 1 GB | Default Python process |
| Data Generator | 512 MB | Batch size 5000–10000 |
| OS + Apps | 2.5 GB | Leave headroom |

**Total**: ~8 GB ✅

---

## When to Consider Upgrading

If you hit these limits, consider:
- **RAM upgrade to 16 GB** → enables full Kafka + larger datasets
- **Docker Desktop** → standardized multi-container deployment
- **WSL2** → Linux-native performance for Kafka/Airflow
- **Cloud VM (Azure/AWS)** → 4-core, 16 GB instance (~$100/month)

---

## What You'll Achieve (Phase 1A)

After completing Phase 1A, you'll have:

✅ Working ClickHouse data warehouse  
✅ 330K+ sales orders loaded (3 years historic)  
✅ 10+ fact & dimension tables  
✅ Sub-second OLAP queries  
✅ Materialized views for dashboard queries  
✅ Foundation for dbt transformations  

This is a **production-ready analytical stack** for a mid-sized company!

---

## Next Document

See `DEPLOYMENT_PHASE_1B_AIRFLOW.md` (coming next) for Airflow orchestration setup.
