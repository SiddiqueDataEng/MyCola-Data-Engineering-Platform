"""
Orchestrator — coordinates all generators and the output writer.
Supports:
  - Historic bulk generation
  - Live streaming (runs in a background thread, stoppable)
"""
import datetime
import threading
import time
import logging
from typing import Callable, Optional

from .config import GeneratorConfig
from .dimension_generator import DimensionGenerator
from .sales_generator import SalesGenerator
from .inventory_generator import InventoryGenerator
from .finance_generator import FinanceGenerator
from .production_generator import ProductionGenerator
from .clickstream_generator import ClickstreamGenerator
from .output_writer import OutputWriter

logger = logging.getLogger(__name__)


class DataOrchestrator:
    """Main entry point for all data generation tasks."""

    def __init__(
        self,
        config: GeneratorConfig,
        status_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ):
        self.cfg = config
        self.status_cb = status_callback or (lambda msg: logger.info(msg))
        self.progress_cb = progress_callback

        self._live_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Cached dim references (built during generate_dimensions)
        self._dim_customers = []
        self._dim_reps = []
        self._dim_suppliers = []

    # ── Historic generation ───────────────────────────────────────────

    def generate_all_historic(self):
        """Run full historic generation: dimensions then all facts."""
        self._log("Starting historic data generation...")

        writer = self._make_writer()

        # 1. Dimensions (fast, small)
        self._log("Generating dimension tables...")
        dim_gen = DimensionGenerator(self.cfg)
        dims = dim_gen.generate_all()
        self._dim_customers = dims["dim_customer"]
        self._dim_reps = dims["dim_sales_rep"]
        self._dim_suppliers = dims["dim_supplier"]

        for table_name, rows in dims.items():
            self._log(f"Writing {table_name} ({len(rows):,} rows)...")
            writer.write_table(table_name, rows, self.cfg.batch_size)
        self._log("Dimension tables written.")

        # 2. Sales facts
        if "sales" in self.cfg.live_domains or True:  # always in historic
            self._log("Generating sales facts...")
            sales_gen = SalesGenerator(self.cfg, self._dim_customers, self._dim_reps)
            orders = sales_gen.generate_historic()
            # Split orders into header and lines tables
            headers = []
            lines = []
            for o in orders:
                lines_data = o.pop("lines", [])
                headers.append(o)
                lines.extend(lines_data)
            self._log(f"Writing fact_sales_order ({len(headers):,} rows)...")
            writer.write_table("fact_sales_order", headers, self.cfg.batch_size)
            self._log(f"Writing fact_sales_order_line ({len(lines):,} rows)...")
            writer.write_table("fact_sales_order_line", lines, self.cfg.batch_size)

        # 3. Inventory facts
        self._log("Generating inventory facts...")
        inv_gen = InventoryGenerator(self.cfg, self._dim_suppliers)
        movements = inv_gen.generate_historic()
        self._log(f"Writing fact_inventory_movement ({len(movements):,} rows)...")
        writer.write_table("fact_inventory_movement", movements, self.cfg.batch_size)

        # 4. Finance facts
        self._log("Generating finance facts...")
        fin_gen = FinanceGenerator(self.cfg, self._dim_customers, self._dim_suppliers)
        gl_entries = fin_gen.generate_historic()
        self._log(f"Writing fact_gl_entry ({len(gl_entries):,} rows)...")
        writer.write_table("fact_gl_entry", gl_entries, self.cfg.batch_size)

        ar_rows = fin_gen.generate_ar()
        self._log(f"Writing fact_accounts_receivable ({len(ar_rows):,} rows)...")
        writer.write_table("fact_accounts_receivable", ar_rows, self.cfg.batch_size)

        ap_rows = fin_gen.generate_ap()
        self._log(f"Writing fact_accounts_payable ({len(ap_rows):,} rows)...")
        writer.write_table("fact_accounts_payable", ap_rows, self.cfg.batch_size)

        # 5. Production facts
        self._log("Generating production facts...")
        prod_gen = ProductionGenerator(self.cfg)
        prod_runs = prod_gen.generate_historic()
        self._log(f"Writing fact_production_run ({len(prod_runs):,} rows)...")
        writer.write_table("fact_production_run", prod_runs, self.cfg.batch_size)

        downtime = prod_gen.generate_downtime()
        writer.write_table("fact_production_downtime", downtime, self.cfg.batch_size)

        inspections = prod_gen.generate_quality_inspection()
        writer.write_table("fact_quality_inspection", inspections, self.cfg.batch_size)

        # 6. Clickstream facts
        self._log("Generating clickstream facts...")
        cs_gen = ClickstreamGenerator(self.cfg, self._dim_customers)
        cs_events = cs_gen.generate_historic()
        self._log(f"Writing fact_clickstream_event ({len(cs_events):,} rows)...")
        writer.write_table("fact_clickstream_event", cs_events, self.cfg.batch_size)

        writer.close()
        self._log("✓ Historic generation complete.")

    # ── Live streaming ────────────────────────────────────────────────

    def start_live_streaming(self):
        """Start a background thread that emits events at configured TPS."""
        if self._live_thread and self._live_thread.is_alive():
            self._log("Live streaming already running.")
            return

        # Ensure dimensions are available
        if not self._dim_customers:
            self._log("Generating dimensions for live mode...")
            dim_gen = DimensionGenerator(self.cfg)
            dims = dim_gen.generate_all()
            self._dim_customers = dims["dim_customer"]
            self._dim_reps = dims["dim_sales_rep"]
            self._dim_suppliers = dims["dim_supplier"]

        self._stop_event.clear()
        self._live_thread = threading.Thread(target=self._live_loop, daemon=True)
        self._live_thread.start()
        self._log("▶ Live streaming started.")

    def stop_live_streaming(self):
        self._stop_event.set()
        if self._live_thread:
            self._live_thread.join(timeout=5)
        self._log("■ Live streaming stopped.")

    def _live_loop(self):
        writer = self._make_writer()
        sales_gen = SalesGenerator(self.cfg, self._dim_customers, self._dim_reps)
        inv_gen = InventoryGenerator(self.cfg, self._dim_suppliers)
        fin_gen = FinanceGenerator(self.cfg, self._dim_customers, self._dim_suppliers)
        prod_gen = ProductionGenerator(self.cfg)
        cs_gen = ClickstreamGenerator(self.cfg, self._dim_customers)

        # Round-robin across domains
        domain_gens = {
            "sales":       lambda: sales_gen.generate_live_event(),
            "inventory":   lambda: inv_gen.generate_live_event(),
            "finance":     lambda: fin_gen.generate_live_event(),
            "production":  lambda: prod_gen.generate_live_event(),
            "clickstream": lambda: cs_gen.generate_live_event(),
        }
        active = [d for d in self.cfg.live_domains if d in domain_gens]
        if not active:
            active = list(domain_gens.keys())

        domain_table_map = {
            "sales":       "fact_sales_order",
            "inventory":   "fact_inventory_movement",
            "finance":     "fact_gl_entry",
            "production":  "fact_production_run",
            "clickstream": "fact_clickstream_event",
        }

        interval = 1.0 / max(self.cfg.live_events_per_second, 0.1)
        event_count = 0

        while not self._stop_event.is_set():
            domain = active[event_count % len(active)]
            try:
                event = domain_gens[domain]()
                table = domain_table_map[domain]
                writer.write_single(table, event)
                event_count += 1
                if event_count % 100 == 0:
                    self._log(f"Live: {event_count} events emitted [{domain}]")
            except Exception as exc:
                logger.error("Live event error in %s: %s", domain, exc)
            time.sleep(interval)

        writer.close()
        self._log(f"Live streaming ended after {event_count} events.")

    # ── Helpers ───────────────────────────────────────────────────────

    def _make_writer(self) -> OutputWriter:
        return OutputWriter(
            output_format=self.cfg.output_format,
            output_dir=self.cfg.output_dir,
            kafka_bootstrap_servers=self.cfg.kafka_bootstrap_servers,
            kafka_topic_prefix=self.cfg.kafka_topic_prefix,
            compress_output=self.cfg.compress_output,
            progress_callback=self.progress_cb,
        )

    def _log(self, msg: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_cb(f"[{timestamp}] {msg}")
