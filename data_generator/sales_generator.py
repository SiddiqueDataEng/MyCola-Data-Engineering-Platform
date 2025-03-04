"""
Generates sales transaction data:
  - fact_sales_order
  - fact_sales_order_line
"""
import datetime
import random
from typing import List, Dict, Any

from .base_generator import BaseGenerator
from .config import GeneratorConfig, PRODUCT_CATALOGUE, WAREHOUSES, TERRITORIES


class SalesGenerator(BaseGenerator):

    def __init__(self, config: GeneratorConfig, dim_customers: List[Dict], dim_reps: List[Dict]):
        super().__init__(config)
        self.customers = dim_customers
        self.reps = [r for r in dim_reps if r["is_active"]]
        self.products = PRODUCT_CATALOGUE
        self.warehouses = WAREHOUSES

    def generate_historic(self) -> List[Dict[str, Any]]:
        """Generate historic sales orders (header + lines)."""
        all_rows = []
        for date in self.date_range():
            vol_factor = self.daily_volume_factor(date)
            num_orders = int(self.cfg.sales_orders_per_day * vol_factor)
            for _ in range(num_orders):
                order = self._create_order(date)
                all_rows.append(order)
                # Duplicate chaos?
                if self.should_duplicate():
                    all_rows.append(order.copy())
        return all_rows

    def generate_live_event(self) -> Dict[str, Any]:
        """Generate a single live sales order event."""
        return self._create_order(datetime.datetime.now().date())

    def _create_order(self, date: datetime.date) -> Dict[str, Any]:
        order_id = self.sequential_id("ORD")
        customer = random.choice(self.customers)
        rep = random.choice(self.reps)
        warehouse = random.choice(self.warehouses)
        order_ts = self.business_hours_ts(date)
        order_ts = self.maybe_late(order_ts)

        # Order lines
        num_lines = random.choices([1, 2, 3, 4, 5], weights=[30, 35, 20, 10, 5])[0]
        lines = []
        total_amount = 0.0
        for line_num in range(1, num_lines + 1):
            sku = random.choice(self.products)
            qty = self.rand_qty(lo=10, hi=500)
            unit_price = self.rand_price(sku["unit_price_pkr"])
            discount_pct = self.rand_discount()
            line_total = qty * unit_price * (1 - discount_pct / 100.0)
            total_amount += line_total
            lines.append({
                "order_line_id":   f"{order_id}-L{line_num:02d}",
                "order_id":        order_id,
                "line_number":     line_num,
                "sku_id":          sku["sku_id"],
                "sku_name":        sku["name"],
                "quantity":        qty,
                "unit_price_pkr":  round(unit_price, 2),
                "discount_pct":    discount_pct,
                "line_total_pkr":  round(line_total, 2),
                "warehouse_id":    warehouse["warehouse_id"],
            })

        # Add GST
        gst_amount = total_amount * 0.17
        grand_total = total_amount + gst_amount

        order_status = random.choices(
            ["Confirmed", "Pending", "Cancelled", "Completed"],
            weights=[70, 15, 5, 10]
        )[0]

        # Schema deviation injection
        extra_fields = {}
        if self.should_deviate_schema():
            extra_fields["unexpected_field"] = "schema_test"

        order = {
            "order_id":          order_id,
            "order_date":        date.isoformat(),
            "order_timestamp":   order_ts.isoformat(),
            "customer_id":       self.maybe_null(customer["customer_id"]),
            "customer_name":     customer["customer_name"],
            "sales_rep_id":      rep["rep_id"],
            "rep_name":          rep["rep_name"],
            "territory_id":      customer["territory_id"],
            "warehouse_id":      warehouse["warehouse_id"],
            "order_status":      order_status,
            "num_lines":         num_lines,
            "total_amount_pkr":  round(total_amount, 2),
            "gst_amount_pkr":    round(gst_amount, 2),
            "grand_total_pkr":   round(grand_total, 2),
            "payment_terms_days": customer["credit_terms_days"],
            "lines":             lines,
            **extra_fields,
        }
        return order
