"""
Generates production / manufacturing data:
  - fact_production_run
  - fact_production_downtime
  - fact_quality_inspection
"""
import datetime
import random
from typing import List, Dict, Any

from .base_generator import BaseGenerator
from .config import GeneratorConfig, PRODUCT_CATALOGUE


PRODUCTION_LINES = [
    {"line_id": "LINE-01", "name": "Bottling Line 1 – 250ml PET",  "capacity_units_hr": 8000},
    {"line_id": "LINE-02", "name": "Bottling Line 2 – 500ml PET",  "capacity_units_hr": 6000},
    {"line_id": "LINE-03", "name": "Bottling Line 3 – 1.5L PET",   "capacity_units_hr": 4000},
    {"line_id": "LINE-04", "name": "Can Line – 250ml",              "capacity_units_hr": 10000},
    {"line_id": "LINE-05", "name": "Water Filling Line",            "capacity_units_hr": 12000},
]

DOWNTIME_REASONS = [
    "Planned Maintenance", "Unplanned Breakdown", "Material Shortage",
    "Quality Hold", "Changeover", "Power Outage", "Operator Break",
]

INSPECTION_RESULTS = ["Pass", "Pass", "Pass", "Pass", "Fail", "Conditional Pass"]


class ProductionGenerator(BaseGenerator):

    def __init__(self, config: GeneratorConfig):
        super().__init__(config)
        self.products = [p for p in PRODUCT_CATALOGUE if p["category"] in ("Cola", "Cola Zero", "Water")]
        self.lines = PRODUCTION_LINES

    def generate_historic(self) -> List[Dict[str, Any]]:
        all_rows = []
        for date in self.date_range():
            factor = self.daily_volume_factor(date)
            num_runs = int(self.cfg.production_runs_per_day * factor)
            for _ in range(num_runs):
                all_rows.append(self._create_production_run(date))
        return all_rows

    def generate_live_event(self) -> Dict[str, Any]:
        return self._create_production_run(datetime.datetime.now().date())

    def _create_production_run(self, date: datetime.date) -> Dict[str, Any]:
        line = random.choice(self.lines)
        sku = random.choice(self.products)
        start_hour = random.randint(6, 20)
        run_hours = random.uniform(1.0, 8.0)
        start_ts = datetime.datetime(date.year, date.month, date.day, start_hour, 0)
        end_ts = start_ts + datetime.timedelta(hours=run_hours)

        planned_units = int(line["capacity_units_hr"] * run_hours)
        efficiency_pct = random.uniform(70, 99)
        actual_units = int(planned_units * efficiency_pct / 100)
        defect_rate_pct = random.uniform(0.1, 2.5)
        defective_units = int(actual_units * defect_rate_pct / 100)

        return {
            "run_id":             self.sequential_id("PROD"),
            "run_date":           date.isoformat(),
            "line_id":            line["line_id"],
            "line_name":          line["name"],
            "sku_id":             sku["sku_id"],
            "sku_name":           sku["name"],
            "shift":              random.choice(["Morning", "Afternoon", "Night"]),
            "start_ts":           start_ts.isoformat(),
            "end_ts":             end_ts.isoformat(),
            "run_hours":          round(run_hours, 2),
            "planned_units":      planned_units,
            "actual_units":       actual_units,
            "defective_units":    defective_units,
            "good_units":         actual_units - defective_units,
            "efficiency_pct":     round(efficiency_pct, 2),
            "defect_rate_pct":    round(defect_rate_pct, 2),
            "oee_pct":            round(efficiency_pct * (1 - defect_rate_pct / 100) * random.uniform(0.85, 0.98), 2),
            "operator_id":        self.maybe_null(f"OP-{random.randint(1, 50):04d}"),
            "batch_number":       f"BATCH-{date.strftime('%Y%m%d')}-{random.randint(1, 99):02d}",
        }

    def generate_downtime(self) -> List[Dict[str, Any]]:
        rows = []
        for date in self.date_range():
            # ~30% of days have some downtime
            if random.random() > 0.30:
                continue
            line = random.choice(self.lines)
            start_hour = random.randint(0, 22)
            start_ts = datetime.datetime(date.year, date.month, date.day, start_hour,
                                         random.randint(0, 59))
            duration_mins = random.choice([15, 30, 45, 60, 90, 120, 180, 240])
            end_ts = start_ts + datetime.timedelta(minutes=duration_mins)
            rows.append({
                "downtime_id":     self.sequential_id("DT"),
                "downtime_date":   date.isoformat(),
                "line_id":         line["line_id"],
                "start_ts":        start_ts.isoformat(),
                "end_ts":          end_ts.isoformat(),
                "duration_mins":   duration_mins,
                "reason":          random.choice(DOWNTIME_REASONS),
                "impact_units":    int(line["capacity_units_hr"] * duration_mins / 60),
                "is_planned":      random.choices([True, False], weights=[40, 60])[0],
            })
        return rows

    def generate_quality_inspection(self) -> List[Dict[str, Any]]:
        rows = []
        for date in self.date_range():
            for line in self.lines:
                # 1-3 inspections per line per day
                for _ in range(random.randint(1, 3)):
                    sku = random.choice(self.products)
                    result = random.choice(INSPECTION_RESULTS)
                    ts = self.business_hours_ts(date)
                    rows.append({
                        "inspection_id":  self.sequential_id("QI"),
                        "inspection_date": date.isoformat(),
                        "inspection_ts":  ts.isoformat(),
                        "line_id":        line["line_id"],
                        "sku_id":         sku["sku_id"],
                        "batch_number":   f"BATCH-{date.strftime('%Y%m%d')}-{random.randint(1, 99):02d}",
                        "result":         result,
                        "ph_level":       round(random.uniform(2.5, 4.0), 2),
                        "brix_level":     round(random.uniform(10.0, 14.0), 2),
                        "co2_volume":     round(random.uniform(3.5, 4.5), 2),
                        "fill_volume_ml": round(sku["size_ml"] * random.uniform(0.98, 1.02), 1),
                        "inspector_id":   f"INS-{random.randint(1, 10):03d}",
                        "comments":       self.maybe_null(self.fake.sentence(nb_words=8)),
                    })
        return rows
