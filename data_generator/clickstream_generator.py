"""
Generates web/app clickstream events for the B2B portal:
  - fact_clickstream_event
Simulates customer portal sessions: browse, add-to-cart, checkout, search, etc.
"""
import datetime
import random
from typing import List, Dict, Any

from .base_generator import BaseGenerator
from .config import GeneratorConfig, PRODUCT_CATALOGUE


EVENT_TYPES = [
    ("page_view",        60),
    ("product_view",     20),
    ("search",           10),
    ("add_to_cart",       5),
    ("remove_from_cart",  2),
    ("checkout_start",    1),
    ("order_placed",      1),
    ("login",             0.5),
    ("logout",            0.5),
]

PAGES = [
    "/", "/products", "/products/{sku}", "/cart", "/checkout",
    "/orders", "/orders/{id}", "/account", "/search",
]

DEVICES = ["desktop", "mobile", "tablet"]
OS_LIST  = ["Windows", "macOS", "Android", "iOS", "Linux"]
BROWSERS = ["Chrome", "Firefox", "Safari", "Edge", "Samsung Internet"]

UTM_SOURCES  = ["google", "facebook", "direct", "email", "whatsapp", None, None]
UTM_MEDIUMS  = ["cpc", "organic", "referral", "email", None]
UTM_CAMPAIGNS = ["summer_promo", "ramadan_sale", "new_product", None, None, None]


class ClickstreamGenerator(BaseGenerator):

    def __init__(self, config: GeneratorConfig, dim_customers: List[Dict]):
        super().__init__(config)
        self.customers = dim_customers
        self.products = PRODUCT_CATALOGUE
        self._event_weights = [w for _, w in EVENT_TYPES]
        self._event_names   = [n for n, _ in EVENT_TYPES]
        # Track active sessions: session_id -> {customer, start_ts, events}
        self._sessions: Dict[str, Dict] = {}

    def generate_historic(self) -> List[Dict[str, Any]]:
        all_rows = []
        for date in self.date_range():
            factor = self.daily_volume_factor(date)
            num_events = int(self.cfg.clickstream_events_per_day * factor)
            for _ in range(num_events):
                all_rows.append(self._create_event(date))
        return all_rows

    def generate_live_event(self) -> Dict[str, Any]:
        return self._create_event(datetime.datetime.now().date())

    def _create_event(self, date: datetime.date) -> Dict[str, Any]:
        customer = random.choice(self.customers)
        session_id = f"SES-{random.randint(1, 10_000_000):010d}"
        event_type = random.choices(self._event_names, weights=self._event_weights, k=1)[0]
        ts = self.business_hours_ts(date)
        ts = self.maybe_late(ts)

        sku = None
        if event_type in ("product_view", "add_to_cart", "remove_from_cart"):
            sku = random.choice(self.products)

        page = random.choice(PAGES)
        if sku and "{sku}" in page:
            page = page.replace("{sku}", sku["sku_id"])

        order_id = None
        if event_type == "order_placed":
            order_id = self.sequential_id("ORD")

        row = {
            "event_id":        self.sequential_id("EVT"),
            "event_timestamp": ts.isoformat(),
            "event_date":      date.isoformat(),
            "session_id":      session_id,
            "customer_id":     self.maybe_null(customer["customer_id"]),
            "territory_id":    customer["territory_id"],
            "event_type":      event_type,
            "page_url":        page,
            "sku_id":          sku["sku_id"] if sku else None,
            "order_id":        order_id,
            "device_type":     random.choice(DEVICES),
            "os":              random.choice(OS_LIST),
            "browser":         random.choice(BROWSERS),
            "ip_address":      self.maybe_null(self.fake.ipv4()),
            "utm_source":      random.choice(UTM_SOURCES),
            "utm_medium":      random.choice(UTM_MEDIUMS),
            "utm_campaign":    random.choice(UTM_CAMPAIGNS),
            "time_on_page_sec": random.randint(1, 300) if event_type == "page_view" else None,
            "search_query":    self.maybe_null(
                random.choice(["cola", "mango", "water", "250ml", "bulk order"]) if event_type == "search" else None
            ),
            "pii_flag":        True,
        }

        # Chaos
        if self.should_deviate_schema():
            row["unexpected_key"] = "schema_chaos"

        return row
