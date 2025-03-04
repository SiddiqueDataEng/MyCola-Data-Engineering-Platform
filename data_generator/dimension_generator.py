"""
Generates dimension tables:
  - dim_customer
  - dim_product (SKU)
  - dim_warehouse
  - dim_territory
  - dim_time
  - dim_sales_rep
  - dim_supplier
"""
import datetime
import random
from typing import List, Dict, Any

from .base_generator import BaseGenerator
from .config import GeneratorConfig, PRODUCT_CATALOGUE, TERRITORIES, WAREHOUSES


class DimensionGenerator(BaseGenerator):

    def __init__(self, config: GeneratorConfig):
        super().__init__(config)

    # ── dim_customer ──────────────────────────────────────────────────

    def generate_customers(self) -> List[Dict[str, Any]]:
        rows = []
        channel_types = ["Retail", "Wholesale", "Horeca", "Modern Trade", "E-Commerce"]
        credit_terms = [0, 7, 14, 30, 45, 60]
        for i in range(1, self.cfg.num_customers + 1):
            ter = random.choice(TERRITORIES)
            channel = random.choice(channel_types)
            credit = random.choice(credit_terms)
            rows.append({
                "customer_id":   f"CUST-{i:06d}",
                "customer_name": self.fake.company(),
                "contact_name":  self.maybe_null(self.fake.name()),
                "phone":         self.maybe_null(self.fake.phone_number()),
                "email":         self.maybe_null(self.fake.email()),
                "address":       self.fake.address().replace("\n", ", "),
                "city":          self.fake.city(),
                "territory_id":  ter["territory_id"],
                "territory_name": ter["name"],
                "channel_type":  channel,
                "credit_limit_pkr": random.choice([50_000, 100_000, 250_000, 500_000, 1_000_000]),
                "credit_terms_days": credit,
                "is_active":     random.choices([True, False], weights=[95, 5])[0],
                "created_at":    self.random_ts(
                    self.cfg.historic_start - datetime.timedelta(days=365),
                    self.cfg.historic_start
                ).isoformat(),
                "pii_flag":      True,   # PII-tagged per design
            })
        return rows

    # ── dim_product ───────────────────────────────────────────────────

    def generate_products(self) -> List[Dict[str, Any]]:
        rows = []
        for p in PRODUCT_CATALOGUE:
            rows.append({
                "sku_id":              p["sku_id"],
                "sku_name":            p["name"],
                "category":            p["category"],
                "size_ml":             p["size_ml"],
                "unit_price_pkr":      p["unit_price_pkr"],
                "cost_price_pkr":      round(p["unit_price_pkr"] * 0.55, 2),
                "units_per_case":      24,
                "is_active":           True,
                "launch_date":         (
                    self.cfg.historic_start - datetime.timedelta(days=random.randint(365, 1825))
                ).date().isoformat(),
                "tax_rate_pct":        17.0,  # Pakistan standard GST
            })
        return rows

    # ── dim_warehouse ─────────────────────────────────────────────────

    def generate_warehouses(self) -> List[Dict[str, Any]]:
        return [
            {
                "warehouse_id":    w["warehouse_id"],
                "warehouse_name":  w["name"],
                "territory_id":    w["territory_id"],
                "capacity_units":  w["capacity_units"],
                "is_active":       True,
            }
            for w in WAREHOUSES
        ]

    # ── dim_territory ─────────────────────────────────────────────────

    def generate_territories(self) -> List[Dict[str, Any]]:
        return [
            {
                "territory_id":   t["territory_id"],
                "territory_name": t["name"],
                "region":         t["region"],
                "country":        "Pakistan",
            }
            for t in TERRITORIES
        ]

    # ── dim_time ──────────────────────────────────────────────────────

    def generate_time_dimension(self) -> List[Dict[str, Any]]:
        rows = []
        current = self.cfg.historic_start.date()
        end = self.cfg.historic_end.date()
        while current <= end:
            rows.append({
                "date_id":        current.strftime("%Y%m%d"),
                "full_date":      current.isoformat(),
                "year":           current.year,
                "quarter":        (current.month - 1) // 3 + 1,
                "month":          current.month,
                "month_name":     current.strftime("%B"),
                "week_of_year":   current.isocalendar()[1],
                "day_of_week":    current.weekday() + 1,
                "day_name":       current.strftime("%A"),
                "is_weekend":     current.weekday() >= 5,
                "fiscal_year":    current.year if current.month >= 7 else current.year - 1,
                "fiscal_quarter": ((current.month - 7) % 12) // 3 + 1,
            })
            current += datetime.timedelta(days=1)
        return rows

    # ── dim_sales_rep ─────────────────────────────────────────────────

    def generate_sales_reps(self) -> List[Dict[str, Any]]:
        rows = []
        for i in range(1, self.cfg.num_sales_reps + 1):
            ter = random.choice(TERRITORIES)
            rows.append({
                "rep_id":         f"REP-{i:04d}",
                "rep_name":       self.fake.name(),
                "email":          self.maybe_null(self.fake.email()),
                "phone":          self.maybe_null(self.fake.phone_number()),
                "territory_id":   ter["territory_id"],
                "hire_date":      (
                    self.cfg.historic_start - datetime.timedelta(days=random.randint(30, 2000))
                ).date().isoformat(),
                "is_active":      random.choices([True, False], weights=[90, 10])[0],
                "monthly_target_pkr": random.choice([500_000, 750_000, 1_000_000, 1_500_000]),
                "pii_flag":       True,
            })
        return rows

    # ── dim_supplier ──────────────────────────────────────────────────

    def generate_suppliers(self) -> List[Dict[str, Any]]:
        materials = ["Sugar", "CO2", "Bottles PET", "Bottles Glass", "Caps",
                     "Labels", "Boxes", "Syrup", "Water Treatment", "Packaging Film"]
        rows = []
        for i in range(1, self.cfg.num_suppliers + 1):
            rows.append({
                "supplier_id":   f"SUP-{i:04d}",
                "supplier_name": self.fake.company(),
                "contact_name":  self.fake.name(),
                "phone":         self.fake.phone_number(),
                "email":         self.maybe_null(self.fake.email()),
                "city":          self.fake.city(),
                "country":       "Pakistan",
                "material_category": random.choice(materials),
                "payment_terms_days": random.choice([30, 45, 60, 90]),
                "is_active":     True,
                "pii_flag":      False,
            })
        return rows

    def generate_all(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "dim_customer":   self.generate_customers(),
            "dim_product":    self.generate_products(),
            "dim_warehouse":  self.generate_warehouses(),
            "dim_territory":  self.generate_territories(),
            "dim_time":       self.generate_time_dimension(),
            "dim_sales_rep":  self.generate_sales_reps(),
            "dim_supplier":   self.generate_suppliers(),
        }
