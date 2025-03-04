#!/usr/bin/env python3
"""
MyCola Data Generator — Headless CLI Mode
Useful for CI/CD pipelines or environments without a display.

Usage:
  python run_headless.py --mode historic
  python run_headless.py --mode live --duration 60
  python run_headless.py --help
"""
import argparse
import datetime
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(__file__))

from data_generator.config import GeneratorConfig
from data_generator.orchestrator import DataOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def parse_args():
    parser = argparse.ArgumentParser(description="MyCola Data Generator — Headless Mode")
    parser.add_argument("--mode", choices=["historic", "live"], default="historic",
                        help="Generation mode: 'historic' (bulk) or 'live' (streaming)")
    parser.add_argument("--start", default="2021-01-01", help="Historic start date YYYY-MM-DD")
    parser.add_argument("--end", default=datetime.date.today().isoformat(),
                        help="Historic end date YYYY-MM-DD")
    parser.add_argument("--format", default="csv", choices=["csv", "json", "parquet", "kafka"],
                        help="Output format")
    parser.add_argument("--output-dir", default="./generated_data", help="Output directory")
    parser.add_argument("--customers", type=int, default=500)
    parser.add_argument("--sales-per-day", type=int, default=300)
    parser.add_argument("--inv-per-day", type=int, default=500)
    parser.add_argument("--fin-per-day", type=int, default=200)
    parser.add_argument("--prod-per-day", type=int, default=20)
    parser.add_argument("--cs-per-day", type=int, default=5000)
    parser.add_argument("--tps", type=float, default=5.0, help="Live events per second")
    parser.add_argument("--duration", type=int, default=60, help="Live mode duration in seconds")
    parser.add_argument("--null-rate", type=float, default=1.0, help="NULL injection rate %%")
    parser.add_argument("--dup-rate", type=float, default=0.5, help="Duplicate rate %%")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--kafka-bootstrap", default="localhost:9092")
    parser.add_argument("--kafka-prefix", default="erp")
    return parser.parse_args()


def main():
    args = parse_args()

    cfg = GeneratorConfig()
    cfg.historic_start = datetime.datetime.strptime(args.start, "%Y-%m-%d")
    cfg.historic_end = datetime.datetime.strptime(args.end, "%Y-%m-%d")
    cfg.num_customers = args.customers
    cfg.sales_orders_per_day = args.sales_per_day
    cfg.inventory_movements_per_day = args.inv_per_day
    cfg.financial_transactions_per_day = args.fin_per_day
    cfg.production_runs_per_day = args.prod_per_day
    cfg.clickstream_events_per_day = args.cs_per_day
    cfg.live_events_per_second = args.tps
    cfg.null_rate = args.null_rate / 100.0
    cfg.duplicate_rate = args.dup_rate / 100.0
    cfg.output_format = args.format
    cfg.output_dir = args.output_dir
    cfg.kafka_bootstrap_servers = args.kafka_bootstrap
    cfg.kafka_topic_prefix = args.kafka_prefix
    cfg.random_seed = args.seed

    orch = DataOrchestrator(cfg)

    if args.mode == "historic":
        logging.info("Running HISTORIC generation from %s to %s", args.start, args.end)
        orch.generate_all_historic()
    else:
        import time
        logging.info("Running LIVE streaming at %.1f events/sec for %d seconds", args.tps, args.duration)
        orch.start_live_streaming()
        time.sleep(args.duration)
        orch.stop_live_streaming()

    logging.info("Done.")


if __name__ == "__main__":
    main()
