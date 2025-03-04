"""
Central configuration dataclass for the MyCola Data Generator.
All values are driven from the UI and passed to every generator.
"""
from dataclasses import dataclass, field
from typing import Optional
import datetime


@dataclass
class GeneratorConfig:
    # ── Time window ───────────────────────────────────────────────────
    historic_start: datetime.datetime = field(
        default_factory=lambda: datetime.datetime(2021, 1, 1)
    )
    historic_end: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now()
    )

    # ── Volume knobs ──────────────────────────────────────────────────
    num_customers: int = 500
    num_skus: int = 80
    num_warehouses: int = 10
    num_territories: int = 8
    num_sales_reps: int = 60
    num_suppliers: int = 30
    num_production_lines: int = 5

    # Daily transaction volumes (approximate)
    sales_orders_per_day: int = 300
    inventory_movements_per_day: int = 500
    financial_transactions_per_day: int = 200
    production_runs_per_day: int = 20
    clickstream_events_per_day: int = 5000

    # ── Live-mode settings ────────────────────────────────────────────
    live_events_per_second: float = 5.0
    live_domains: list = field(default_factory=lambda: [
        "sales", "inventory", "finance", "production", "clickstream"
    ])

    # ── Data-quality chaos settings ───────────────────────────────────
    null_rate: float = 0.01          # fraction of fields that become NULL
    duplicate_rate: float = 0.005    # fraction of records duplicated
    late_arrival_rate: float = 0.02  # fraction with out-of-order timestamps
    schema_deviation_rate: float = 0.001  # fraction that deviate from schema

    # ── Output settings ───────────────────────────────────────────────
    output_format: str = "csv"       # csv | json | parquet | kafka
    output_dir: str = "./generated_data"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_prefix: str = "erp"

    # ── Misc ──────────────────────────────────────────────────────────
    random_seed: Optional[int] = 42
    batch_size: int = 10_000         # rows per file chunk
    compress_output: bool = False


# MyCola product catalogue — used by all generators
PRODUCT_CATALOGUE = [
    {"sku_id": f"SKU-{i:04d}", "name": name, "category": cat,
     "unit_price_pkr": price, "size_ml": size}
    for i, (name, cat, price, size) in enumerate([
        ("MyCola Classic 250ml",   "Cola",         35,  250),
        ("MyCola Classic 500ml",   "Cola",         65,  500),
        ("MyCola Classic 1.5L",    "Cola",        120, 1500),
        ("MyCola Zero 250ml",      "Cola Zero",    40,  250),
        ("MyCola Zero 500ml",      "Cola Zero",    70,  500),
        ("MyCola Zero 1.5L",       "Cola Zero",   130, 1500),
        ("MyOrange 250ml",         "Fruit Drink",  30,  250),
        ("MyOrange 500ml",         "Fruit Drink",  55,  500),
        ("MyOrange 1L",            "Fruit Drink",  95, 1000),
        ("MyLemon 250ml",          "Fruit Drink",  30,  250),
        ("MyLemon 500ml",          "Fruit Drink",  55,  500),
        ("MyMango 250ml",          "Fruit Drink",  35,  250),
        ("MyMango 500ml",          "Fruit Drink",  60,  500),
        ("MyMango 1L",             "Fruit Drink", 100, 1000),
        ("MyWater 500ml",          "Water",        25,  500),
        ("MyWater 1.5L",           "Water",        50, 1500),
        ("MyWater 5L",             "Water",       130, 5000),
        ("MySoda Lemon 250ml",     "Soda",         30,  250),
        ("MySoda Ginger 250ml",    "Soda",         30,  250),
        ("MyEnergy 250ml",         "Energy",       75,  250),
    ], start=1)
]

TERRITORIES = [
    {"territory_id": f"TER-{i:03d}", "name": name, "region": region}
    for i, (name, region) in enumerate([
        ("Karachi Central",   "Sindh"),
        ("Karachi East",      "Sindh"),
        ("Karachi West",      "Sindh"),
        ("Lahore North",      "Punjab"),
        ("Lahore South",      "Punjab"),
        ("Islamabad/RWP",     "Punjab"),
        ("Peshawar",          "KPK"),
        ("Quetta",            "Balochistan"),
    ], start=1)
]

WAREHOUSES = [
    {"warehouse_id": f"WH-{i:03d}", "name": name, "territory_id": f"TER-{ter:03d}",
     "capacity_units": cap}
    for i, (name, ter, cap) in enumerate([
        ("Karachi Central DC",  1, 500_000),
        ("Karachi East DC",     2, 300_000),
        ("Karachi West DC",     3, 200_000),
        ("Lahore North DC",     4, 450_000),
        ("Lahore South DC",     5, 350_000),
        ("Islamabad DC",        6, 400_000),
        ("Peshawar DC",         7, 250_000),
        ("Quetta DC",           8, 150_000),
        ("Hub Plant Store",     1, 600_000),
        ("Faisalabad Store",    4, 300_000),
    ], start=1)
]
