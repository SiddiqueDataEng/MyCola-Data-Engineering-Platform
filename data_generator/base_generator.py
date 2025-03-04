"""
Base generator class with shared utilities (Faker, random, chaos injection).
"""
import random
import datetime
import uuid
from typing import Any, Dict, List, Optional

from faker import Faker

from .config import GeneratorConfig


class BaseGenerator:
    """Shared state and helpers for all domain generators."""

    def __init__(self, config: GeneratorConfig):
        self.cfg = config
        seed = config.random_seed
        random.seed(seed)
        self.fake = Faker("en_PK")
        Faker.seed(seed)
        self._row_counter = 0

    # ── ID helpers ────────────────────────────────────────────────────

    def new_uuid(self) -> str:
        return str(uuid.uuid4())

    def sequential_id(self, prefix: str) -> str:
        self._row_counter += 1
        return f"{prefix}-{self._row_counter:010d}"

    # ── Timestamp helpers ─────────────────────────────────────────────

    def random_ts(
        self,
        start: datetime.datetime,
        end: datetime.datetime,
    ) -> datetime.datetime:
        delta = end - start
        random_seconds = random.uniform(0, delta.total_seconds())
        return start + datetime.timedelta(seconds=random_seconds)

    def business_hours_ts(self, date: datetime.date) -> datetime.datetime:
        """Return a random timestamp within business hours (08:00-22:00 PKT)."""
        hour = random.randint(8, 21)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        return datetime.datetime(date.year, date.month, date.day, hour, minute, second)

    # ── Chaos injection ───────────────────────────────────────────────

    def maybe_null(self, value: Any) -> Optional[Any]:
        """Return None with probability null_rate, else value."""
        if random.random() < self.cfg.null_rate:
            return None
        return value

    def maybe_late(self, ts: datetime.datetime) -> datetime.datetime:
        """Shift timestamp backwards to simulate late arrival."""
        if random.random() < self.cfg.late_arrival_rate:
            lag = random.randint(60, 3600)  # 1 min – 1 hour lag
            return ts - datetime.timedelta(seconds=lag)
        return ts

    def should_duplicate(self) -> bool:
        return random.random() < self.cfg.duplicate_rate

    def should_deviate_schema(self) -> bool:
        return random.random() < self.cfg.schema_deviation_rate

    # ── Numeric helpers ───────────────────────────────────────────────

    def rand_qty(self, lo: int = 1, hi: int = 500) -> int:
        return random.randint(lo, hi)

    def rand_price(self, base: float, spread: float = 0.05) -> float:
        """Price with ±spread% variation."""
        factor = 1.0 + random.uniform(-spread, spread)
        return round(base * factor, 2)

    def rand_discount(self) -> float:
        """Discount percentage 0–25%."""
        tiers = [0, 0, 0, 2, 5, 5, 10, 15, 20, 25]
        return random.choice(tiers)

    # ── Date range iterator ───────────────────────────────────────────

    def date_range(self):
        """Yield each date from historic_start to historic_end."""
        current = self.cfg.historic_start.date()
        end = self.cfg.historic_end.date()
        while current <= end:
            yield current
            current += datetime.timedelta(days=1)

    # ── Weekday / seasonality weight ─────────────────────────────────

    def daily_volume_factor(self, date: datetime.date) -> float:
        """
        Simulate realistic seasonality:
        - Ramadan bump (+40%)
        - Summer peak June-Aug (+30%)
        - Weekend dip (-20%)
        - Monday/Friday slight boost (+10%)
        """
        factor = 1.0
        # Weekend dip
        if date.weekday() == 6:  # Sunday
            factor *= 0.80
        elif date.weekday() == 5:  # Saturday
            factor *= 0.90
        # Summer heat = more cold drinks
        if date.month in (5, 6, 7, 8):
            factor *= 1.30
        # Winter slow
        if date.month in (12, 1):
            factor *= 0.85
        return factor
