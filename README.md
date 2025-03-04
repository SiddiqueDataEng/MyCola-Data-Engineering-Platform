# MyCola Pakistan — Data Generator

**Complete, Production-Grade Data Simulator for the MyCola Data Engineering Platform**

---

## Overview

This data generator creates **realistic, configurable, historic and live data** for all domains of the MyCola Pakistan data infrastructure:

- ✅ **Sales** (orders, order lines, customer transactions)
- ✅ **Inventory** (receipts, dispatches, transfers, adjustments, daily snapshots)
- ✅ **Finance** (GL entries, accounts receivable, accounts payable)
- ✅ **Production** (production runs, downtime events, quality inspections)
- ✅ **Clickstream** (web/app portal events: page views, searches, add-to-cart, checkouts)
- ✅ **Dimensions** (customers, products/SKUs, warehouses, territories, time, sales reps, suppliers)

### Key Features

🎯 **Full GUI (Tkinter)** — no web browser needed, runs natively on Windows/macOS/Linux  
📊 **Historic Mode** — bulk-generate years of past data to CSV/JSON/Parquet  
📡 **Live Streaming Mode** — real-time event generation at configurable TPS to Kafka or files  
🔧 **Fully Configurable** — every volume knob, date range, data quality chaos setting exposed in UI  
🧪 **Data Quality Chaos** — inject NULL values, duplicates, late arrivals, schema deviations to test platform resilience  
🚀 **Headless CLI Mode** — for CI/CD pipelines and environments without a display  
📦 **Multi-format Output** — CSV, NDJSON, Parquet, Kafka topics  
🔁 **Realistic Patterns** — seasonality (summer peaks, Ramadan bumps), weekday/weekend cycles, business hours

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     DATA GENERATOR ARCHITECTURE                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  UI Layer (Tkinter GUI)                                       │   │
│  │    - Configuration Panel (volumes, dates, chaos, output)     │   │
│  │    - Live Logs & Status Panel                                │   │
│  │    - Progress Bar                                            │   │
│  │    - Action Buttons (Generate Historic / Start-Stop Live)    │   │
│  └───────────────────────────┬──────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Orchestrator                                                 │   │
│  │    - Coordinates all generators                              │   │
│  │    - Manages historic bulk generation                        │   │
│  │    - Manages live streaming thread (stoppable)               │   │
│  └────────────┬──────────────────────────────────────────┬──────┘   │
│               │                                           │          │
│               ▼                                           ▼          │
│  ┌──────────────────────────────┐   ┌───────────────────────────┐  │
│  │   Domain Generators          │   │   Output Writer           │  │
│  │  • DimensionGenerator        │   │  • CSV (chunked)          │  │
│  │  • SalesGenerator            │   │  • NDJSON                 │  │
│  │  • InventoryGenerator        │   │  • Parquet                │  │
│  │  • FinanceGenerator          │   │  • Kafka (JSON)           │  │
│  │  • ProductionGenerator       │   │  • Compression support    │  │
│  │  • ClickstreamGenerator      │   └───────────────────────────┘  │
│  │                              │                                   │
│  │  Each extends BaseGenerator  │                                   │
│  │  • Faker (realistic PK data) │                                   │
│  │  • Chaos injection           │                                   │
│  │  • Seasonality / weekday     │                                   │
│  └──────────────────────────────┘                                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r data_generator/requirements.txt
```

Dependencies: `faker`, `pandas`, `pyarrow`, `numpy`, `kafka-python`, `tqdm`, `python-dateutil`

### 2. Launch GUI

```bash
python run_data_generator.py
```

The Tkinter GUI will open. Configure your generation parameters:

- **Time Window**: Historic start/end dates
- **Volume Knobs**: # of customers, SKUs, warehouses, sales reps, etc.
- **Daily Transaction Volumes**: orders/day, inventory movements/day, etc.
- **Live Mode**: events per second (TPS)
- **Data Quality Chaos**: NULL rate, duplicate rate, late arrival rate, schema deviation rate
- **Output Settings**: format (CSV/JSON/Parquet/Kafka), directory, Kafka bootstrap servers

Then click **"Generate Historic Data"** or **"Start Live Streaming"**.

### 3. Headless CLI Mode (No GUI)

For CI/CD or headless servers:

```bash
# Generate 3 years of historic data to CSV
python run_headless.py --mode historic --start 2021-01-01 --end 2023-12-31 --format csv --output-dir ./data

# Stream live events to Kafka for 120 seconds at 10 events/sec
python run_headless.py --mode live --duration 120 --tps 10 --format kafka --kafka-bootstrap localhost:9092

# See all options
python run_headless.py --help
```

---

## Generated Data Schema

### Dimensions

| Table | Primary Key | Rows (default) | Description |
|---|---|---|---|
| `dim_customer` | `customer_id` | 500 | B2B customers with PII (contact, address, credit terms) |
| `dim_product` | `sku_id` | 20 | MyCola product catalogue (SKUs, prices, sizes) |
| `dim_warehouse` | `warehouse_id` | 10 | Distribution centers and plant stores |
| `dim_territory` | `territory_id` | 8 | Sales territories (Karachi, Lahore, Islamabad, etc.) |
| `dim_time` | `date_id` | ~2000 | Date dimension (fiscal year, quarter, weekday, etc.) |
| `dim_sales_rep` | `rep_id` | 60 | Sales representatives with PII |
| `dim_supplier` | `supplier_id` | 30 | Raw material suppliers |

### Facts — Sales

| Table | Primary Key | Volume (default) | Description |
|---|---|---|---|
| `fact_sales_order` | `order_id` | 300/day | Sales order headers with customer, rep, territory, amounts |
| `fact_sales_order_line` | `order_line_id` | ~600/day | Order line items with SKU, quantity, price, discount |

### Facts — Inventory

| Table | Primary Key | Volume (default) | Description |
|---|---|---|---|
| `fact_inventory_movement` | `movement_id` | 500/day | Receipts, dispatches, transfers, adjustments |
| `fact_inventory_snapshot` | `snapshot_id` | SKUs × WH/day | Daily closing stock per SKU per warehouse |

### Facts — Finance

| Table | Primary Key | Volume (default) | Description |
|---|---|---|---|
| `fact_gl_entry` | `transaction_id` | 200/day | General ledger transactions (revenue, expense, asset, liability entries) |
| `fact_accounts_receivable` | `ar_id` | ~80/day | Customer invoices: due dates, overdue days, payment status |
| `fact_accounts_payable` | `ap_id` | ~60/day | Supplier bills: due dates, payment status |

### Facts — Production

| Table | Primary Key | Volume (default) | Description |
|---|---|---|---|
| `fact_production_run` | `run_id` | 20/day | Bottling line runs: actual vs planned units, defect rates, OEE |
| `fact_production_downtime` | `downtime_id` | ~6/day | Downtime events with reason, duration, impact |
| `fact_quality_inspection` | `inspection_id` | ~60/day | QC checks: pH, Brix, CO₂, fill volume |

### Facts — Clickstream

| Table | Primary Key | Volume (default) | Description |
|---|---|---|---|
| `fact_clickstream_event` | `event_id` | 5000/day | B2B portal events: page views, product views, cart actions, orders |

---

## Configuration Options (UI)

### Time Window
- **Historic Start**: Start date for bulk generation (YYYY-MM-DD)
- **Historic End**: End date for bulk generation

### Volume Knobs
- **Customers**: # of unique customers (default: 500)
- **SKUs**: # of unique products (default: 80, based on MyCola catalogue)
- **Warehouses**: # of warehouses/DCs (default: 10)
- **Territories**: # of sales territories (default: 8)
- **Sales Reps**: # of sales representatives (default: 60)
- **Suppliers**: # of suppliers (default: 30)

### Daily Transaction Volumes
- **Sales Orders /day**: average daily orders (default: 300)
- **Inventory Movements /day**: receipts, dispatches, etc. (default: 500)
- **Financial Txns /day**: GL entries (default: 200)
- **Production Runs /day**: bottling line runs (default: 20)
- **Clickstream Events /day**: portal events (default: 5000)

### Live Mode
- **Events per Second**: TPS for live streaming (default: 5.0)

### Data Quality Chaos
- **NULL Rate (%)**: fraction of fields that become NULL (default: 1%)
- **Duplicate Rate (%)**: fraction of records duplicated (default: 0.5%)
- **Late Arrival Rate (%)**: fraction with out-of-order timestamps (default: 2%)
- **Schema Deviation Rate (%)**: fraction that inject unexpected fields (default: 0.1%)

### Output Settings
- **Output Format**: `csv` | `json` (NDJSON) | `parquet` | `kafka`
- **Output Directory**: local filesystem path (default: `./generated_data`)
- **Kafka Bootstrap**: Kafka broker address (default: `localhost:9092`)
- **Kafka Topic Prefix**: topic prefix (default: `erp`)
- **Batch Size**: rows per file chunk for CSV/JSON/Parquet (default: 10,000)
- **Compress Output**: gzip compression for CSV/JSON (default: off)
- **Random Seed**: reproducibility seed (default: 42)

---

## Realistic Data Patterns

### Seasonality

- **Summer Peak (May–Aug)**: +30% volume (higher cold drink demand)
- **Ramadan Bump**: +40% volume (simulated via month-based factor)
- **Winter Slowdown (Dec–Jan)**: -15% volume

### Weekday / Weekend Variation

- **Sunday**: -20% volume (lighter trading day)
- **Saturday**: -10% volume
- **Monday / Friday**: +10% volume (stock-up days)

### Business Hours

All timestamps are generated within **08:00–22:00 PKT** (Pakistan Time), reflecting MyCola's operational hours.

### PII Tagging

All records with customer names, contact details, or employee info are flagged with `"pii_flag": true` to enable downstream masking/encryption tests.

---

## Output Formats

### 1. CSV (Default)

```
generated_data/
├── dim_customer_0.csv
├── dim_product_0.csv
├── fact_sales_order_0.csv
├── fact_sales_order_1.csv  (if > batch_size)
└── ...
```

**Chunking**: Files are split into chunks of `batch_size` rows (default: 10,000).  
**Nested fields**: Lists/dicts are serialized to JSON strings.

### 2. JSON (NDJSON)

```
generated_data/
├── dim_customer_0.jsonl
├── fact_sales_order_0.jsonl
└── ...
```

Newline-delimited JSON. Each line is a valid JSON object.

### 3. Parquet

```
generated_data/
├── dim_customer_0.parquet
├── fact_sales_order_0.parquet
└── ...
```

Columnar format (Snappy compression). Ideal for analytics and data warehouses.

### 4. Kafka

Events are published to Kafka topics in real-time:

```
erp.dim_customer
erp.fact_sales_order
erp.fact_inventory_movement
...
```

Each event is JSON-serialized.

---

## Testing Data Quality Features

The generator intentionally injects **chaos** to validate the platform's data quality, CDC, and DLQ (dead-letter queue) handling:

| Chaos Type | Injection Point | Expected Platform Behavior |
|---|---|---|
| **NULL values** | Random fields set to `null` | dbt tests should flag NOT NULL violations; Great Expectations should catch null rates > threshold |
| **Duplicates** | Entire record repeated | Deduplication logic in staging layer should drop duplicates |
| **Late arrivals** | Timestamp shifted back 1–60 min | CDC late-arrival watermarking should handle; Airflow SLA monitoring should alert |
| **Schema deviations** | Random field `unexpected_field` added | Schema Registry validation should route to quarantine zone; Atlas catalog should flag schema version mismatch |

These are **configurable** via the UI sliders.

---

## Example Use Cases

### 1. Seed a Fresh ClickHouse Warehouse

Generate 2 years of historic data to Parquet, then bulk-load into ClickHouse:

```bash
python run_headless.py --mode historic --start 2022-01-01 --end 2023-12-31 --format parquet --output-dir ./clickhouse_seed
```

Then use ClickHouse's `INSERT FROM INFILE` or Airbyte to ingest.

### 2. Test CDC Pipeline End-to-End

Stream live sales events to Kafka for 5 minutes at 20 TPS:

```bash
python run_headless.py --mode live --duration 300 --tps 20 --format kafka --kafka-bootstrap kafka-broker:9092
```

Watch the events flow through Debezium → Kafka → ClickHouse staging → dbt transformations.

### 3. Stress-Test dbt Incremental Models

Generate 10,000 sales orders/day for 30 days (300K orders):

```bash
python run_headless.py --sales-per-day 10000 --start 2024-01-01 --end 2024-01-30 --format csv
```

Load into staging and measure dbt incremental run performance.

### 4. Validate Great Expectations Data Quality Checks

Inject high NULL and duplicate rates:

```bash
python run_headless.py --null-rate 10 --dup-rate 5 --start 2024-01-01 --end 2024-01-07 --format json
```

Run GX expectation suites and verify ERROR-level checks block mart promotion.

---

## Folder Structure

```
clickstream_sales_analytics/
├── data_generator/
│   ├── __init__.py
│   ├── config.py                     # GeneratorConfig dataclass + product catalogue
│   ├── base_generator.py             # BaseGenerator with Faker, chaos injection, helpers
│   ├── dimension_generator.py        # Generates all dimension tables
│   ├── sales_generator.py            # Sales orders + lines
│   ├── inventory_generator.py        # Inventory movements + snapshots
│   ├── finance_generator.py          # GL entries, AR, AP
│   ├── production_generator.py       # Production runs, downtime, QC
│   ├── clickstream_generator.py      # Web/app clickstream events
│   ├── output_writer.py              # Multi-format output (CSV/JSON/Parquet/Kafka)
│   ├── orchestrator.py               # DataOrchestrator (historic + live)
│   ├── requirements.txt
│   └── ui/
│       ├── __init__.py
│       └── app.py                    # Tkinter GUI
├── run_data_generator.py             # GUI launcher
├── run_headless.py                   # CLI launcher
└── README_DATA_GENERATOR.md          # This file
```

---

## Extending the Generator

### Add a New Fact Table

1. **Create a new generator class** in `data_generator/new_fact_generator.py`:
   ```python
   from .base_generator import BaseGenerator

   class NewFactGenerator(BaseGenerator):
       def generate_historic(self):
           rows = []
           for date in self.date_range():
               # generate records for this date
               rows.append(...)
           return rows
   ```

2. **Wire it into the orchestrator** (`orchestrator.py`):
   ```python
   new_gen = NewFactGenerator(self.cfg, ...)
   rows = new_gen.generate_historic()
   writer.write_table("fact_new_table", rows, self.cfg.batch_size)
   ```

3. **Update the UI** to expose new config sliders if needed.

### Change Product Catalogue

Edit `config.py` → `PRODUCT_CATALOGUE` list. The generator will automatically use the updated SKUs.

### Add Custom Chaos Logic

Override `BaseGenerator` methods or add new chaos injection methods:

```python
def maybe_flip_sign(self, value: float) -> float:
    if random.random() < self.cfg.sign_flip_rate:
        return -value
    return value
```

---

## Performance

On a modern laptop (8-core, 16 GB RAM):

| Task | Volume | Duration |
|---|---|---|
| Generate 3 years historic (500 customers, 300 orders/day) | ~330,000 sales orders | ~3–5 minutes |
| Generate 1 year clickstream (5000 events/day) | ~1.8M events | ~2 minutes |
| Live streaming to Kafka (10 TPS) | 10 events/sec | Real-time, no lag |

**Tip**: Use Parquet for large datasets to achieve 5–10× faster writes and smaller file sizes.

---

## Troubleshooting

### GUI doesn't launch on Windows

Ensure `tk` (Tkinter) is installed. It ships with most Python distributions. If missing:

```bash
pip install tk
```

### Kafka connection errors in live mode

Check `kafka_bootstrap_servers` config. Ensure Kafka broker is reachable:

```bash
nc -zv localhost 9092
```

### High memory usage during historic generation

Reduce `batch_size` in config (default: 10,000 → try 5,000).

---

## License

This data generator is part of the MyCola Pakistan Data Engineering Platform codebase.  
Internal use only.

---

## Contact

For questions or issues, contact the MyCola Data Engineering team.

**Enjoy generating data!** 🚀

# MyCola Platform — Next Steps: Windows Native Execution Plan

**My system**: Windows 10 Pro, Intel i3 @ 3.2 GHz, 8 GB RAM, Python 3.13  
**Status**: ✅ Data generated   🔲 ClickHouse needed   🔲 Data loaded   🔲 BI layer

---

## Phase Roadmap

```
Phase 1A  ← YOU ARE HERE
Data Generator → CSV Files → ClickHouse → SQL Queries  ← START NOW (today)
        ↓
Phase 1B  (next week)
ClickHouse → dbt transformations → Materialized Views → Superset Dashboards
        ↓
Phase 2   (week 3-4)
Add Kafka streaming + live CDC simulation
        ↓
Phase 3   (month 2)
Add Airflow orchestration + full pipeline automation
```

---

## Phase 1A: Install ClickHouse + Load Data

ClickHouse on Windows requires **WSL2** (Windows Subsystem for Linux). Choose one method:

### Method A: WSL2 + ClickHouse (Recommended)

**Step 1 — Install WSL2 + ClickHouse (~30 minutes, requires reboot)**

Open **PowerShell as Administrator** (right-click > Run as Administrator) and run:

```powershell
# Quick automated installer
powershell -ExecutionPolicy Bypass -File "F:\siddi\clickstream_sales_analytics\platform\install_wsl_clickhouse.ps1"
```

This will:
1. Enable WSL2 features
2. Install Ubuntu 22.04 LTS
3. Prompt for reboot

**After reboot**, open **Ubuntu** (Start menu > Ubuntu) and run:

```bash
# Install ClickHouse in Ubuntu
curl https://clickhouse.com/install.sh | sudo bash

# Start ClickHouse
sudo clickhouse start

# Test connection
clickhouse-client

# Type "SELECT 1" to verify, then "exit"
```

---

### Method B: Docker Desktop (Alternative, ~20 minutes, no reboot)

If you prefer Docker:

1. Download and install Docker Desktop: https://docs.docker.com/desktop/install/windows-install/
2. After installing, open **PowerShell** and run:

```powershell
# Start ClickHouse in Docker
docker run -d -p 9000:9000 -p 8123:8123 --name mycola_clickhouse `
  -v F:\siddi\clickstream_sales_analytics\clickhouse_data:/var/lib/clickhouse `
  clickhouse/clickhouse-server

# Verify it's running
docker ps
```

---

### Step 2 — Apply Database Schema (both methods)

```powershell
# Install the Python ClickHouse driver
pip install clickhouse-driver pandas pyarrow

# Apply all DDL (creates databases, tables, materialized views)
python F:\siddi\clickstream_sales_analytics\platform\apply_schema.py
```

Expected output:
```
✓ CREATE DATABASE IF NOT EXISTS staging_db
✓ CREATE DATABASE IF NOT EXISTS mart_db
✓ CREATE TABLE IF NOT EXISTS mart_db.dim_customer ...
... (18 tables + 2 materialized views)
✓ All tables and views created successfully!
```

### Step 4 — Generate Data (if not done yet)

```powershell
# Launch the GUI to generate 3 years of historic data
python F:\siddi\clickstream_sales_analytics\run_data_generator.py
```

Or use headless CLI for speed:

```powershell
python F:\siddi\clickstream_sales_analytics\run_headless.py `
  --mode historic `
  --start 2021-01-01 `
  --end 2023-12-31 `
  --format csv `
  --output-dir "F:\siddi\clickstream_sales_analytics\generated_data"
```

Estimated time: ~3–5 minutes.

### Step 5 — Load Data into ClickHouse

```powershell
# Load all tables from generated_data/ into ClickHouse
python F:\siddi\clickstream_sales_analytics\platform\load_data.py `
  --data-dir "F:\siddi\clickstream_sales_analytics\generated_data" `
  --host localhost `
  --port 9000
```

Expected output:
```
Loading dim_customer → mart_db.dim_customer ... ✓ 500 rows
Loading fact_sales_order → mart_db.fact_sales_order ... ✓ 327,450 rows
...
TOTAL ROWS: ~1,800,000 rows in ~45s
```

### Step 6 — Verify and Query!

```powershell
# Open the ClickHouse SQL client
C:\mycola\clickhouse\client.cmd
```

In the ClickHouse client, run:

```sql
-- Check everything loaded correctly
SELECT 'dim_customer' AS tbl, count() AS rows FROM mart_db.dim_customer
UNION ALL SELECT 'fact_sales_order', count() FROM mart_db.fact_sales_order
UNION ALL SELECT 'fact_clickstream_event', count() FROM mart_db.fact_clickstream_event;

-- Your first analytics query: Monthly revenue by territory
SELECT
    toStartOfMonth(order_date) AS month,
    territory_id,
    round(sum(grand_total_pkr) / 1000000, 2) AS revenue_millions_pkr
FROM mart_db.fact_sales_order
WHERE order_status = 'Confirmed'
GROUP BY month, territory_id
ORDER BY month DESC, revenue_millions_pkr DESC
LIMIT 20;
```

More queries in: `F:\siddi\clickstream_sales_analytics\platform\verify_queries.sql`

---

## Phase 1B: Add dbt Transformations (Next Week)

Once Phase 1A is working:

```powershell
# Install dbt with ClickHouse adapter
pip install dbt-core dbt-clickhouse

# Initialize dbt project (run from project root)
dbt init mycola_transforms

# Configure profiles.yml for ClickHouse
# C:\Users\<yourname>\.dbt\profiles.yml
```

**profiles.yml**:
```yaml
mycola_transforms:
  target: dev
  outputs:
    dev:
      type: clickhouse
      schema: mart_db
      host: localhost
      port: 9000
      user: default
      password: ""
      secure: False
```

dbt models will live in:
```
F:\siddi\clickstream_sales_analytics\dbt_project\
├── models\
│   ├── staging\        ← raw CSV → typed tables
│   ├── intermediate\   ← business logic joins
│   └── mart\           ← star schema (fact + dim)
```

---

## Phase 1C: Add Apache Superset (BI Dashboards)

```powershell
# Install Superset (Python package)
pip install apache-superset

# Initialize database and create admin user
superset db upgrade
superset fab create-admin
superset init

# Start Superset
superset run -p 8088 --with-threads --reload --debugger
```

Open browser: http://localhost:8088

Connect Superset to ClickHouse:
- **Datasource URL**: `clickhousedb://default@localhost:8123/mart_db`
- **Driver**: `clickhouse-connect` (install: `pip install clickhouse-connect`)

Build dashboards:
1. Sales Performance (daily/weekly/monthly revenue by territory)
2. Inventory Levels by SKU and Warehouse
3. Financial P&L Summary
4. Production Throughput & OEE

---

## Phase 2: Add Kafka Streaming (Week 3-4)

### Install Kafka on Windows

```powershell
# Download Kafka (Windows)
$kafkaVer = "3.7.0"
Invoke-WebRequest `
  -Uri "https://downloads.apache.org/kafka/$kafkaVer/kafka_2.13-$kafkaVer.tgz" `
  -OutFile "C:\mycola\kafka_$kafkaVer.tgz"

# Extract (requires 7-Zip or WSL)
# ...

# Start ZooKeeper (Terminal 1)
C:\mycola\kafka\bin\windows\zookeeper-server-start.bat C:\mycola\kafka\config\zookeeper.properties

# Start Kafka Broker (Terminal 2) — with reduced heap for 8 GB RAM
$env:KAFKA_HEAP_OPTS = "-Xmx512m -Xms256m"
C:\mycola\kafka\bin\windows\kafka-server-start.bat C:\mycola\kafka\config\server.properties
```

Then switch the Data Generator to Kafka output mode and watch events flow!

---

## Phase 3: Add Airflow Orchestration (Month 2)

```powershell
# Install Airflow (Windows-native)
pip install apache-airflow==2.8.0 --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.8.0/constraints-3.11.txt"

# Initialize Airflow metadata DB (SQLite for dev)
airflow db init

# Create admin user
airflow users create `
  --username admin `
  --firstname MyCola `
  --lastname Admin `
  --role Admin `
  --email admin@mycola.local `
  --password admin123

# Start webserver (Terminal 1)
airflow webserver --port 8080

# Start scheduler (Terminal 2)
airflow scheduler
```

Open browser: http://localhost:8080

---

## Memory & Performance Tips (Your 8 GB System)

### Run only what you need at each phase:

| Phase | Running Processes | Memory Used |
|---|---|---|
| 1A | ClickHouse | ~2 GB |
| 1B | ClickHouse + dbt (CLI, transient) | ~2.5 GB |
| 1C | ClickHouse + Superset | ~3.5 GB |
| 2 | ClickHouse + Kafka + ZooKeeper | ~4.5 GB |
| 3 | ClickHouse + Kafka + Airflow | ~5.5 GB |

**Tip**: Stop processes you're not actively using. All state is persisted to disk.

### ClickHouse memory tuning for 8 GB:

In `C:\mycola\clickhouse\config.xml`, the script already sets:
```xml
<max_server_memory_usage>4000000000</max_server_memory_usage>
```

This caps ClickHouse at 4 GB, leaving headroom for OS and other tools.

---

## Summary: What You'll Have After Each Phase

| Phase | What Works |
|---|---|
| **1A** (today) | ClickHouse warehouse + 3 years of MyCola data loaded + SQL analytics |
| **1B** (next week) | dbt staging/mart models + incremental transforms + data tests |
| **1C** (week 3) | Superset dashboards: sales, inventory, P&L, production |
| **2** (week 4) | Kafka streaming + live CDC simulation + real-time ingestion |
| **3** (month 2) | Full Airflow-orchestrated pipeline + scheduling + monitoring |

---

## Estimated Total Setup Time

| Phase | Time |
|---|---|
| 1A: ClickHouse + Load Data | ~45 minutes |
| 1B: dbt | ~2 hours |
| 1C: Superset | ~2 hours |
| 2: Kafka | ~3 hours |
| 3: Airflow | ~3 hours |
| **Total for full stack** | **~1.5 working days** |

This is a complete, working, production-grade data engineering platform on your local machine.

---

## Start right now:

```powershell
# Terminal 1 — Run this first
powershell -ExecutionPolicy Bypass -File "F:\siddi\clickstream_sales_analytics\platform\setup_clickhouse.ps1"
```
