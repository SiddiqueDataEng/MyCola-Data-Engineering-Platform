# Getting Started — MyCola Data Generator

**Welcome!** This guide helps you run the data generator in under 5 minutes.

---

## Prerequisites

- **Python 3.8+** installed (check: `python --version`)
- **Internet connection** (for installing dependencies)

---

## Option 1: Quick Start (Windows — Double-Click)

1. **Double-click** `quickstart.cmd`
2. The script will:
   - Check Python
   - Install dependencies
   - Launch the GUI
3. Configure your generation parameters in the UI
4. Click **"Generate Historic Data"** or **"Start Live Streaming"**
5. Watch the logs panel for progress!

---

## Option 2: Manual Steps (All Platforms)

### Step 1: Install Dependencies

Open a terminal in the project directory and run:

```bash
pip install -r data_generator/requirements.txt
```

### Step 2: Launch GUI

```bash
python run_data_generator.py
```

The Tkinter GUI will open.

### Step 3: Configure and Generate

**Left Panel (Configuration):**
- Set your date range (e.g., 2021-01-01 to 2023-12-31)
- Adjust volume knobs (# of customers, orders/day, etc.)
- Choose output format: CSV, JSON, Parquet, or Kafka
- Configure output directory

**Right Panel (Logs & Status):**
- Click **"Generate Historic Data"** to bulk-generate years of data
- Click **"Start Live Streaming"** to emit real-time events
- Watch the logs for progress updates

---

## Option 3: Headless CLI Mode (No GUI)

For servers or CI/CD pipelines:

```bash
# Generate 3 years of historic data to CSV
python run_headless.py --mode historic --start 2021-01-01 --end 2023-12-31 --format csv

# Stream live events to Kafka for 60 seconds
python run_headless.py --mode live --duration 60 --tps 10 --format kafka --kafka-bootstrap localhost:9092

# See all options
python run_headless.py --help
```

---

## Quick Validation

After generation, check the output directory (default: `./generated_data`):

```bash
# Windows
dir generated_data

# Linux/macOS
ls -lh generated_data/
```

You should see files like:
- `dim_customer_0.csv`
- `fact_sales_order_0.csv`
- `fact_inventory_movement_0.csv`
- etc.

---

## Example Configuration

A good starting point for realistic simulation:

| Parameter | Value |
|---|---|
| Historic Start | 2021-01-01 |
| Historic End | 2023-12-31 |
| Customers | 500 |
| Sales Orders /day | 300 |
| Inventory Movements /day | 500 |
| Financial Txns /day | 200 |
| Production Runs /day | 20 |
| Clickstream Events /day | 5000 |
| Output Format | CSV |
| Batch Size | 10,000 |
| Random Seed | 42 (for reproducibility) |

This generates **~330,000 sales orders** over 3 years.

---

## Troubleshooting

### GUI doesn't open

**Windows**: Ensure Tkinter is installed. It ships with most Python distributions. If missing:
```bash
pip install tk
```

**Linux**: Install `python3-tk`:
```bash
sudo apt-get install python3-tk   # Debian/Ubuntu
sudo yum install python3-tkinter  # RHEL/CentOS
```

### Kafka connection errors

Check that your Kafka broker is reachable:
```bash
nc -zv localhost 9092  # Linux/macOS
Test-NetConnection -ComputerName localhost -Port 9092  # Windows PowerShell
```

If Kafka is not running, the generator will fall back to JSON output with a warning.

### Memory issues

If generating very large datasets (5+ years with high daily volumes):
- **Reduce Batch Size** in the config (default: 10,000 → 5,000)
- **Generate in chunks** (e.g., 1 year at a time)
- **Use Parquet format** (more memory-efficient than CSV)

---

## What's Next?

1. **Explore the data**: Open the generated CSV/JSON files to see the schema
2. **Load into your warehouse**: Use Airbyte, dbt seeds, or ClickHouse `INSERT FROM INFILE`
3. **Test CDC pipelines**: Stream live events to Kafka and watch them flow through your platform
4. **Validate data quality**: Inject chaos (NULL rates, duplicates) to test your DQ checks

---

## Need Help?

- Read the full documentation: `README_DATA_GENERATOR.md`
- Run smoke test: `python smoke_test.py`
- Check the spec files: `.kiro/specs/mycola-data-infrastructure/`

**Happy generating!** 🚀
