"""
MyCola Data Generator — Tkinter GUI
Complete UI for configuring and running historic + live data generation.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import datetime
import threading
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from data_generator.config import GeneratorConfig
from data_generator.orchestrator import DataOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class DataGeneratorApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MyCola Data Generator — v1.0")
        self.root.geometry("1200x850")
        self.root.resizable(True, True)

        self.orchestrator: DataOrchestrator | None = None
        self.generation_thread: threading.Thread | None = None

        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#0066cc", height=60)
        header.pack(side=tk.TOP, fill=tk.X)
        tk.Label(header, text="MyCola Pakistan — Data Generator UI",
                 font=("Arial", 18, "bold"), fg="white", bg="#0066cc").pack(pady=12)

        # Main container
        container = tk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel: Configuration
        left = tk.LabelFrame(container, text="Configuration", font=("Arial", 12, "bold"),
                             padx=10, pady=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))

        # Right panel: Status & Logs
        right = tk.LabelFrame(container, text="Logs & Status", font=("Arial", 12, "bold"),
                              padx=10, pady=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self._build_config_panel(left)
        self._build_status_panel(right)

    def _build_config_panel(self, parent: tk.Frame):
        # Scrollable config area
        canvas = tk.Canvas(parent, width=420, height=700)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        config_frame = tk.Frame(canvas)
        config_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=config_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # == Time Window ==
        row = 0
        tk.Label(config_frame, text="Time Window", font=("Arial", 11, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(5, 3))
        row += 1

        tk.Label(config_frame, text="Historic Start:").grid(row=row, column=0, sticky="w")
        self.historic_start_var = tk.StringVar(value="2021-01-01")
        tk.Entry(config_frame, textvariable=self.historic_start_var, width=20).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        tk.Label(config_frame, text="Historic End:").grid(row=row, column=0, sticky="w")
        self.historic_end_var = tk.StringVar(value=datetime.date.today().isoformat())
        tk.Entry(config_frame, textvariable=self.historic_end_var, width=20).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        # == Volume Knobs ==
        tk.Label(config_frame, text="Volume Knobs", font=("Arial", 11, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(10, 3))
        row += 1

        self.volume_vars = {}
        for label, default in [
            ("Customers", 500),
            ("SKUs", 80),
            ("Warehouses", 10),
            ("Territories", 8),
            ("Sales Reps", 60),
            ("Suppliers", 30),
            ("Production Lines", 5),
        ]:
            tk.Label(config_frame, text=f"# {label}:").grid(row=row, column=0, sticky="w")
            var = tk.IntVar(value=default)
            self.volume_vars[label.lower().replace(" ", "_")] = var
            tk.Entry(config_frame, textvariable=var, width=10).grid(row=row, column=1, sticky="w", pady=2)
            row += 1

        # Daily transaction volumes
        tk.Label(config_frame, text="Daily Transaction Volumes", font=("Arial", 11, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(10, 3))
        row += 1

        self.daily_vars = {}
        for label, default in [
            ("Sales Orders /day", 300),
            ("Inventory Movements /day", 500),
            ("Financial Txns /day", 200),
            ("Production Runs /day", 20),
            ("Clickstream Events /day", 5000),
        ]:
            tk.Label(config_frame, text=label).grid(row=row, column=0, sticky="w")
            var = tk.IntVar(value=default)
            self.daily_vars[label.lower().replace(" /day", "").replace(" ", "_")] = var
            tk.Entry(config_frame, textvariable=var, width=10).grid(row=row, column=1, sticky="w", pady=2)
            row += 1

        # == Live Mode ==
        tk.Label(config_frame, text="Live Mode Settings", font=("Arial", 11, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(10, 3))
        row += 1

        tk.Label(config_frame, text="Events per Second:").grid(row=row, column=0, sticky="w")
        self.live_tps_var = tk.DoubleVar(value=5.0)
        tk.Entry(config_frame, textvariable=self.live_tps_var, width=10).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        # == Data Quality Chaos ==
        tk.Label(config_frame, text="Data Quality Chaos", font=("Arial", 11, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(10, 3))
        row += 1

        self.chaos_vars = {}
        for label, default in [
            ("NULL Rate (%)", 1.0),
            ("Duplicate Rate (%)", 0.5),
            ("Late Arrival Rate (%)", 2.0),
            ("Schema Deviation Rate (%)", 0.1),
        ]:
            tk.Label(config_frame, text=label).grid(row=row, column=0, sticky="w")
            var = tk.DoubleVar(value=default)
            self.chaos_vars[label.lower().replace(" rate (%)", "").replace(" ", "_")] = var
            tk.Entry(config_frame, textvariable=var, width=10).grid(row=row, column=1, sticky="w", pady=2)
            row += 1

        # == Output Settings ==
        tk.Label(config_frame, text="Output Settings", font=("Arial", 11, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(10, 3))
        row += 1

        tk.Label(config_frame, text="Output Format:").grid(row=row, column=0, sticky="w")
        self.output_format_var = tk.StringVar(value="csv")
        format_combo = ttk.Combobox(config_frame, textvariable=self.output_format_var,
                                     values=["csv", "json", "parquet", "kafka"], width=15, state="readonly")
        format_combo.grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        tk.Label(config_frame, text="Output Directory:").grid(row=row, column=0, sticky="w")
        self.output_dir_var = tk.StringVar(value="./generated_data")
        dir_frame = tk.Frame(config_frame)
        dir_frame.grid(row=row, column=1, sticky="w", pady=2)
        tk.Entry(dir_frame, textvariable=self.output_dir_var, width=20).pack(side=tk.LEFT)
        tk.Button(dir_frame, text="...", command=self._browse_dir, width=3).pack(side=tk.LEFT, padx=(3, 0))
        row += 1

        tk.Label(config_frame, text="Kafka Bootstrap:").grid(row=row, column=0, sticky="w")
        self.kafka_bootstrap_var = tk.StringVar(value="localhost:9092")
        tk.Entry(config_frame, textvariable=self.kafka_bootstrap_var, width=20).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        tk.Label(config_frame, text="Kafka Topic Prefix:").grid(row=row, column=0, sticky="w")
        self.kafka_prefix_var = tk.StringVar(value="erp")
        tk.Entry(config_frame, textvariable=self.kafka_prefix_var, width=20).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        tk.Label(config_frame, text="Batch Size:").grid(row=row, column=0, sticky="w")
        self.batch_size_var = tk.IntVar(value=10_000)
        tk.Entry(config_frame, textvariable=self.batch_size_var, width=10).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        self.compress_var = tk.BooleanVar(value=False)
        tk.Checkbutton(config_frame, text="Compress Output", variable=self.compress_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=5)
        row += 1

        # Random seed
        tk.Label(config_frame, text="Random Seed:").grid(row=row, column=0, sticky="w")
        self.seed_var = tk.IntVar(value=42)
        tk.Entry(config_frame, textvariable=self.seed_var, width=10).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

    def _build_status_panel(self, parent: tk.Frame):
        # Progress bar
        self.progress_var = tk.IntVar(value=0)
        self.progress_label = tk.Label(parent, text="Ready", font=("Arial", 10))
        self.progress_label.pack(pady=(5, 2))
        self.progress_bar = ttk.Progressbar(parent, variable=self.progress_var, maximum=100, length=500)
        self.progress_bar.pack(pady=(0, 10))

        # Logs
        tk.Label(parent, text="Activity Log:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.log_text = scrolledtext.ScrolledText(parent, height=25, width=70, state=tk.DISABLED,
                                                   font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Action buttons
        button_frame = tk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_generate_historic = tk.Button(button_frame, text="Generate Historic Data",
                                                bg="#0066cc", fg="white", font=("Arial", 11, "bold"),
                                                command=self._on_generate_historic, height=2)
        self.btn_generate_historic.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.btn_start_live = tk.Button(button_frame, text="Start Live Streaming",
                                         bg="#00aa44", fg="white", font=("Arial", 11, "bold"),
                                         command=self._on_start_live, height=2)
        self.btn_start_live.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))

        self.btn_stop_live = tk.Button(button_frame, text="Stop Live",
                                        bg="#cc0000", fg="white", font=("Arial", 11, "bold"),
                                        command=self._on_stop_live, state=tk.DISABLED, height=2)
        self.btn_stop_live.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

    # ── Callbacks ─────────────────────────────────────────────────────

    def _browse_dir(self):
        path = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if path:
            self.output_dir_var.set(path)

    def _build_config(self) -> GeneratorConfig:
        cfg = GeneratorConfig()
        try:
            cfg.historic_start = datetime.datetime.strptime(self.historic_start_var.get(), "%Y-%m-%d")
            cfg.historic_end = datetime.datetime.strptime(self.historic_end_var.get(), "%Y-%m-%d")
        except ValueError as exc:
            messagebox.showerror("Date Error", f"Invalid date format: {exc}")
            raise

        cfg.num_customers = self.volume_vars["customers"].get()
        cfg.num_skus = self.volume_vars["skus"].get()
        cfg.num_warehouses = self.volume_vars["warehouses"].get()
        cfg.num_territories = self.volume_vars["territories"].get()
        cfg.num_sales_reps = self.volume_vars["sales_reps"].get()
        cfg.num_suppliers = self.volume_vars["suppliers"].get()
        cfg.num_production_lines = self.volume_vars["production_lines"].get()

        cfg.sales_orders_per_day = self.daily_vars["sales_orders"].get()
        cfg.inventory_movements_per_day = self.daily_vars["inventory_movements"].get()
        cfg.financial_transactions_per_day = self.daily_vars["financial_txns"].get()
        cfg.production_runs_per_day = self.daily_vars["production_runs"].get()
        cfg.clickstream_events_per_day = self.daily_vars["clickstream_events"].get()

        cfg.live_events_per_second = self.live_tps_var.get()

        cfg.null_rate = self.chaos_vars["null"] .get() / 100.0
        cfg.duplicate_rate = self.chaos_vars["duplicate"].get() / 100.0
        cfg.late_arrival_rate = self.chaos_vars["late_arrival"].get() / 100.0
        cfg.schema_deviation_rate = self.chaos_vars["schema_deviation"].get() / 100.0

        cfg.output_format = self.output_format_var.get()
        cfg.output_dir = self.output_dir_var.get()
        cfg.kafka_bootstrap_servers = self.kafka_bootstrap_var.get()
        cfg.kafka_topic_prefix = self.kafka_prefix_var.get()
        cfg.batch_size = self.batch_size_var.get()
        cfg.compress_output = self.compress_var.get()
        cfg.random_seed = self.seed_var.get()

        return cfg

    def _on_generate_historic(self):
        if self.generation_thread and self.generation_thread.is_alive():
            messagebox.showwarning("Busy", "Historic generation already in progress.")
            return
        try:
            cfg = self._build_config()
        except Exception:
            return
        self.btn_generate_historic.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

        def run():
            try:
                orch = DataOrchestrator(cfg, self._log, self._progress)
                orch.generate_all_historic()
                self.root.after(0, lambda: messagebox.showinfo("Done", "Historic data generation complete!"))
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Generation failed:\n{exc}"))
            finally:
                self.root.after(0, lambda: self.btn_generate_historic.config(state=tk.NORMAL))

        self.generation_thread = threading.Thread(target=run, daemon=True)
        self.generation_thread.start()

    def _on_start_live(self):
        if self.orchestrator:
            messagebox.showinfo("Info", "Live streaming already active.")
            return
        try:
            cfg = self._build_config()
        except Exception:
            return
        self.orchestrator = DataOrchestrator(cfg, self._log, self._progress)
        self.orchestrator.start_live_streaming()
        self.btn_start_live.config(state=tk.DISABLED)
        self.btn_stop_live.config(state=tk.NORMAL)

    def _on_stop_live(self):
        if not self.orchestrator:
            return
        self.orchestrator.stop_live_streaming()
        self.orchestrator = None
        self.btn_start_live.config(state=tk.NORMAL)
        self.btn_stop_live.config(state=tk.DISABLED)

    def _log(self, msg: str):
        def append():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(0, append)

    def _progress(self, current: int, total: int, label: str):
        pct = int((current / total) * 100) if total > 0 else 0
        def update():
            self.progress_var.set(pct)
            self.progress_label.config(text=f"{label}: {current:,} / {total:,} ({pct}%)")
        self.root.after(0, update)


def main():
    root = tk.Tk()
    app = DataGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
