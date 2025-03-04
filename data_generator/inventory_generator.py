"""
Generates inventory fact data:
  - fact_inventory_movement  (receipts, transfers, dispatches, adjustments)
  - fact_inventory_snapshot  (daily closing stock per SKU per warehouse)
"""
import datetime
import random
from typing import List, Dict, Any

from .base_generator import BaseGenerator
from .config import GeneratorConfig, PRODUCT_CATALOGUE, WAREHOUSES


class InventoryGenerator(BaseGenerator):

    MOVEMENT_TYPES = ["Receipt", "Dispatch", "Transfer_In", "Transfer_Out",
                      "Adjustment_Positive", "Adjustment_Negative", "Return"]

    def __init__(self, config: GeneratorConfig, dim_suppliers: List[Dict]):
        super().__init__(config)
        self.products = PRODUCT_CATALOGUE
        self.warehouses = WAREHOUSES
        self.suppliers = dim_suppliers

        # Initialise stock levels per (sku, warehouse)
        self.stock: Dict[tuple, int] = {}
        for sku in self.products:
            for wh in self.warehouses:
                # Start with random opening stock
                self.stock[(sku["sku_id"], wh["warehouse_id"])] = random.randint(500, 20_000)

    # ── Movements ─────────────────────────────────────────────────────

    def generate_historic(self) -> List[Dict[str, Any]]:
        all_rows = []
        for date in self.date_range():
            factor = self.daily_volume_factor(date)
            num_movements = int(self.cfg.inventory_movements_per_day * factor)
            for _ in range(num_movements):
                row = self._create_movement(date)
                all_rows.append(row)
                if self.should_duplicate():
                    all_rows.append(row.copy())
        return all_rows

    def generate_live_event(self) -> Dict[str, Any]:
        return self._create_movement(datetime.datetime.now().date())

    def _create_movement(self, date: datetime.date) -> Dict[str, Any]:
        sku = random.choice(self.products)
        warehouse = random.choice(self.warehouses)
        mv_type = random.choices(
            self.MOVEMENT_TYPES,
            weights=[20, 40, 10, 10, 5, 5, 10]
        )[0]

        qty = self.rand_qty(lo=10, hi=2000)
        key = (sku["sku_id"], warehouse["warehouse_id"])

        # Update stock
        if mv_type in ("Receipt", "Transfer_In", "Adjustment_Positive", "Return"):
            self.stock[key] = self.stock.get(key, 0) + qty
        else:
            self.stock[key] = max(0, self.stock.get(key, 0) - qty)

        supplier_id = None
        if mv_type == "Receipt":
            supplier_id = self.maybe_null(random.choice(self.suppliers)["supplier_id"])

        ts = self.business_hours_ts(date)
        ts = self.maybe_late(ts)

        return {
            "movement_id":      self.sequential_id("INV"),
            "movement_date":    date.isoformat(),
            "movement_ts":      ts.isoformat(),
            "sku_id":           sku["sku_id"],
            "sku_name":         sku["name"],
            "warehouse_id":     warehouse["warehouse_id"],
            "movement_type":    mv_type,
            "quantity":         qty,
            "closing_stock":    self.stock[key],
            "unit_cost_pkr":    round(sku["unit_price_pkr"] * 0.55, 2),
            "total_cost_pkr":   round(qty * sku["unit_price_pkr"] * 0.55, 2),
            "supplier_id":      supplier_id,
            "reference_doc":    self.new_uuid(),
            "is_reconciled":    random.choices([True, False], weights=[95, 5])[0],
        }

    # ── Daily snapshot ────────────────────────────────────────────────

    def generate_snapshot(self, date: datetime.date) -> List[Dict[str, Any]]:
        rows = []
        for sku in self.products:
            for wh in self.warehouses:
                key = (sku["sku_id"], wh["warehouse_id"])
                stock_qty = self.stock.get(key, 0)
                rows.append({
                    "snapshot_id":     self.sequential_id("SNAP"),
                    "snapshot_date":   date.isoformat(),
                    "sku_id":          sku["sku_id"],
                    "warehouse_id":    wh["warehouse_id"],
                    "closing_stock":   stock_qty,
                    "reorder_level":   1000,
                    "is_below_reorder": stock_qty < 1000,
                })
        return rows
