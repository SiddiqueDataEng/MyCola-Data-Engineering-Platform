"""
Generates financial fact data (Oracle DB equivalent):
  - fact_financial_transaction  (GL entries)
  - fact_accounts_receivable
  - fact_accounts_payable
"""
import datetime
import random
from typing import List, Dict, Any

from .base_generator import BaseGenerator
from .config import GeneratorConfig


GL_ACCOUNTS = [
    {"account_id": "4001", "account_name": "Sales Revenue",          "account_type": "Revenue"},
    {"account_id": "4002", "account_name": "Other Income",           "account_type": "Revenue"},
    {"account_id": "5001", "account_name": "Cost of Goods Sold",     "account_type": "Expense"},
    {"account_id": "5002", "account_name": "Production Labour",      "account_type": "Expense"},
    {"account_id": "5003", "account_name": "Distribution Freight",   "account_type": "Expense"},
    {"account_id": "5004", "account_name": "Marketing Expense",      "account_type": "Expense"},
    {"account_id": "5005", "account_name": "Admin Expense",          "account_type": "Expense"},
    {"account_id": "6001", "account_name": "Depreciation",           "account_type": "Expense"},
    {"account_id": "1001", "account_name": "Cash & Equivalents",     "account_type": "Asset"},
    {"account_id": "1002", "account_name": "Accounts Receivable",    "account_type": "Asset"},
    {"account_id": "1003", "account_name": "Inventory",              "account_type": "Asset"},
    {"account_id": "2001", "account_name": "Accounts Payable",       "account_type": "Liability"},
    {"account_id": "2002", "account_name": "GST Payable",            "account_type": "Liability"},
    {"account_id": "3001", "account_name": "Share Capital",          "account_type": "Equity"},
    {"account_id": "3002", "account_name": "Retained Earnings",      "account_type": "Equity"},
]

COST_CENTRES = [
    "CC-SALES", "CC-PRODUCTION", "CC-LOGISTICS", "CC-MARKETING",
    "CC-ADMIN", "CC-FINANCE", "CC-HR",
]


class FinanceGenerator(BaseGenerator):

    def __init__(self, config: GeneratorConfig, dim_customers: List[Dict], dim_suppliers: List[Dict]):
        super().__init__(config)
        self.customers = dim_customers
        self.suppliers = dim_suppliers

    def generate_historic(self) -> List[Dict[str, Any]]:
        all_rows = []
        for date in self.date_range():
            factor = self.daily_volume_factor(date)
            num_txns = int(self.cfg.financial_transactions_per_day * factor)
            for _ in range(num_txns):
                row = self._create_gl_entry(date)
                all_rows.append(row)
        return all_rows

    def generate_live_event(self) -> Dict[str, Any]:
        return self._create_gl_entry(datetime.datetime.now().date())

    def _create_gl_entry(self, date: datetime.date) -> Dict[str, Any]:
        account = random.choice(GL_ACCOUNTS)
        amount = round(random.uniform(5_000, 5_000_000), 2)
        entry_type = "Debit" if account["account_type"] in ("Asset", "Expense") else "Credit"
        if random.random() < 0.5:
            entry_type = "Credit" if entry_type == "Debit" else "Debit"

        ts = self.business_hours_ts(date)
        ts = self.maybe_late(ts)

        return {
            "transaction_id":    self.sequential_id("FIN"),
            "transaction_date":  date.isoformat(),
            "transaction_ts":    ts.isoformat(),
            "fiscal_year":       date.year if date.month >= 7 else date.year - 1,
            "fiscal_period":     f"FY{date.year % 100:02d}-P{((date.month - 7) % 12) + 1:02d}",
            "account_id":        account["account_id"],
            "account_name":      account["account_name"],
            "account_type":      account["account_type"],
            "entry_type":        entry_type,
            "amount_pkr":        amount,
            "cost_centre":       random.choice(COST_CENTRES),
            "reference_number":  self.new_uuid(),
            "description":       self.maybe_null(self.fake.sentence(nb_words=6)),
            "posted_by":         self.maybe_null(self.fake.user_name()),
            "is_reconciled":     random.choices([True, False], weights=[88, 12])[0],
            "currency":          "PKR",
            "exchange_rate":     1.0,
        }

    # ── Accounts Receivable ───────────────────────────────────────────

    def generate_ar(self) -> List[Dict[str, Any]]:
        rows = []
        for date in self.date_range():
            factor = self.daily_volume_factor(date)
            num_ar = int((self.cfg.financial_transactions_per_day * 0.4) * factor)
            for _ in range(num_ar):
                customer = random.choice(self.customers)
                invoice_amount = round(random.uniform(10_000, 2_000_000), 2)
                due_date = date + datetime.timedelta(days=customer["credit_terms_days"])
                days_overdue = (datetime.date.today() - due_date).days
                status = "Paid" if days_overdue < -5 else (
                    "Overdue" if days_overdue > 0 else "Current"
                )
                rows.append({
                    "ar_id":           self.sequential_id("AR"),
                    "invoice_date":    date.isoformat(),
                    "due_date":        due_date.isoformat(),
                    "customer_id":     customer["customer_id"],
                    "invoice_amount_pkr": invoice_amount,
                    "paid_amount_pkr": invoice_amount if status == "Paid" else round(random.uniform(0, invoice_amount), 2),
                    "outstanding_pkr": 0.0 if status == "Paid" else invoice_amount,
                    "status":          status,
                    "days_overdue":    max(0, days_overdue),
                    "pii_flag":        True,
                })
        return rows

    # ── Accounts Payable ──────────────────────────────────────────────

    def generate_ap(self) -> List[Dict[str, Any]]:
        rows = []
        for date in self.date_range():
            factor = self.daily_volume_factor(date)
            num_ap = int((self.cfg.financial_transactions_per_day * 0.3) * factor)
            for _ in range(num_ap):
                supplier = random.choice(self.suppliers)
                bill_amount = round(random.uniform(20_000, 5_000_000), 2)
                due_date = date + datetime.timedelta(days=supplier["payment_terms_days"])
                status = random.choices(["Pending", "Approved", "Paid", "Disputed"], weights=[30, 40, 25, 5])[0]
                rows.append({
                    "ap_id":           self.sequential_id("AP"),
                    "bill_date":       date.isoformat(),
                    "due_date":        due_date.isoformat(),
                    "supplier_id":     supplier["supplier_id"],
                    "bill_amount_pkr": bill_amount,
                    "paid_amount_pkr": bill_amount if status == "Paid" else 0.0,
                    "outstanding_pkr": 0.0 if status == "Paid" else bill_amount,
                    "status":          status,
                })
        return rows
