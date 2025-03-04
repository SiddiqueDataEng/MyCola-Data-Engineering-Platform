"""
Apply the MyCola ClickHouse schema — creates all databases, dimension tables,
fact tables, and materialized views.
"""
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

try:
    from clickhouse_driver import Client
except ImportError:
    log.error("clickhouse-driver not installed. Run: pip install clickhouse-driver pandas")
    sys.exit(1)

DDL_STATEMENTS = [
    # ── Databases ─────────────────────────────────────────────────────
    "CREATE DATABASE IF NOT EXISTS staging_db",
    "CREATE DATABASE IF NOT EXISTS mart_db",

    # ── dim_customer ──────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.dim_customer
    (
        customer_id         String,
        customer_name       String,
        contact_name        Nullable(String),
        phone               Nullable(String),
        email               Nullable(String),
        address             String,
        city                String,
        territory_id        String,
        territory_name      String,
        channel_type        String,
        credit_limit_pkr    UInt32,
        credit_terms_days   UInt16,
        is_active           UInt8,
        created_at          DateTime,
        pii_flag            UInt8
    )
    ENGINE = MergeTree()
    ORDER BY customer_id
    """,

    # ── dim_product ───────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.dim_product
    (
        sku_id            String,
        sku_name          String,
        category          String,
        size_ml           UInt16,
        unit_price_pkr    Float32,
        cost_price_pkr    Float32,
        units_per_case    UInt16,
        is_active         UInt8,
        launch_date       Date,
        tax_rate_pct      Float32
    )
    ENGINE = MergeTree()
    ORDER BY sku_id
    """,

    # ── dim_warehouse ─────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.dim_warehouse
    (
        warehouse_id      String,
        warehouse_name    String,
        territory_id      String,
        capacity_units    UInt32,
        is_active         UInt8
    )
    ENGINE = MergeTree()
    ORDER BY warehouse_id
    """,

    # ── dim_territory ─────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.dim_territory
    (
        territory_id      String,
        territory_name    String,
        region            String,
        country           String
    )
    ENGINE = MergeTree()
    ORDER BY territory_id
    """,

    # ── dim_time ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.dim_time
    (
        date_id           String,
        full_date         Date,
        year              UInt16,
        quarter           UInt8,
        month             UInt8,
        month_name        String,
        week_of_year      UInt8,
        day_of_week       UInt8,
        day_name          String,
        is_weekend        UInt8,
        fiscal_year       UInt16,
        fiscal_quarter    UInt8
    )
    ENGINE = MergeTree()
    ORDER BY date_id
    """,

    # ── dim_sales_rep ─────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.dim_sales_rep
    (
        rep_id                String,
        rep_name              String,
        email                 Nullable(String),
        phone                 Nullable(String),
        territory_id          String,
        hire_date             Date,
        is_active             UInt8,
        monthly_target_pkr    UInt32,
        pii_flag              UInt8
    )
    ENGINE = MergeTree()
    ORDER BY rep_id
    """,

    # ── dim_supplier ──────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.dim_supplier
    (
        supplier_id           String,
        supplier_name         String,
        contact_name          String,
        phone                 String,
        email                 Nullable(String),
        city                  String,
        country               String,
        material_category     String,
        payment_terms_days    UInt16,
        is_active             UInt8,
        pii_flag              UInt8
    )
    ENGINE = MergeTree()
    ORDER BY supplier_id
    """,

    # ── fact_sales_order ──────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.fact_sales_order
    (
        order_id            String,
        order_date          Date,
        order_timestamp     DateTime,
        customer_id         Nullable(String),
        customer_name       String,
        sales_rep_id        String,
        rep_name            String,
        territory_id        String,
        warehouse_id        String,
        order_status        String,
        num_lines           UInt16,
        total_amount_pkr    Float32,
        gst_amount_pkr      Float32,
        grand_total_pkr     Float32,
        payment_terms_days  UInt16
    )
    ENGINE = MergeTree()
    PARTITION BY toYYYYMM(order_date)
    ORDER BY (territory_id, order_date, order_id)
    """,

    # ── fact_sales_order_line ─────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.fact_sales_order_line
    (
        order_line_id       String,
        order_id            String,
        line_number         UInt16,
        sku_id              String,
        sku_name            String,
        quantity            UInt32,
        unit_price_pkr      Float32,
        discount_pct        Float32,
        line_total_pkr      Float32,
        warehouse_id        String
    )
    ENGINE = MergeTree()
    ORDER BY (order_id, line_number)
    """,

    # ── fact_inventory_movement ───────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.fact_inventory_movement
    (
        movement_id         String,
        movement_date       Date,
        movement_ts         DateTime,
        sku_id              String,
        sku_name            String,
        warehouse_id        String,
        movement_type       String,
        quantity            Int32,
        closing_stock       Int32,
        unit_cost_pkr       Float32,
        total_cost_pkr      Float32,
        supplier_id         Nullable(String),
        reference_doc       String,
        is_reconciled       UInt8
    )
    ENGINE = MergeTree()
    PARTITION BY toYYYYMM(movement_date)
    ORDER BY (warehouse_id, sku_id, movement_date)
    """,

    # ── fact_gl_entry ─────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.fact_gl_entry
    (
        transaction_id      String,
        transaction_date    Date,
        transaction_ts      DateTime,
        fiscal_year         UInt16,
        fiscal_period       String,
        account_id          String,
        account_name        String,
        account_type        String,
        entry_type          String,
        amount_pkr          Float32,
        cost_centre         String,
        reference_number    String,
        description         Nullable(String),
        posted_by           Nullable(String),
        is_reconciled       UInt8,
        currency            String,
        exchange_rate       Float32
    )
    ENGINE = MergeTree()
    PARTITION BY toYYYYMM(transaction_date)
    ORDER BY (account_id, transaction_date, transaction_id)
    """,

    # ── fact_accounts_receivable ──────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.fact_accounts_receivable
    (
        ar_id                   String,
        invoice_date            Date,
        due_date                Date,
        customer_id             String,
        invoice_amount_pkr      Float32,
        paid_amount_pkr         Float32,
        outstanding_pkr         Float32,
        status                  String,
        days_overdue            Int32,
        pii_flag                UInt8
    )
    ENGINE = MergeTree()
    PARTITION BY toYYYYMM(invoice_date)
    ORDER BY (customer_id, invoice_date, ar_id)
    """,

    # ── fact_accounts_payable ─────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.fact_accounts_payable
    (
        ap_id                   String,
        bill_date               Date,
        due_date                Date,
        supplier_id             String,
        bill_amount_pkr         Float32,
        paid_amount_pkr         Float32,
        outstanding_pkr         Float32,
        status                  String
    )
    ENGINE = MergeTree()
    PARTITION BY toYYYYMM(bill_date)
    ORDER BY (supplier_id, bill_date, ap_id)
    """,

    # ── fact_production_run ───────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.fact_production_run
    (
        run_id              String,
        run_date            Date,
        line_id             String,
        line_name           String,
        sku_id              String,
        sku_name            String,
        shift               String,
        start_ts            DateTime,
        end_ts              DateTime,
        run_hours           Float32,
        planned_units       UInt32,
        actual_units        UInt32,
        defective_units     UInt32,
        good_units          UInt32,
        efficiency_pct      Float32,
        defect_rate_pct     Float32,
        oee_pct             Float32,
        operator_id         Nullable(String),
        batch_number        String
    )
    ENGINE = MergeTree()
    PARTITION BY toYYYYMM(run_date)
    ORDER BY (line_id, run_date, run_id)
    """,

    # ── fact_production_downtime ──────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.fact_production_downtime
    (
        downtime_id         String,
        downtime_date       Date,
        line_id             String,
        start_ts            DateTime,
        end_ts              DateTime,
        duration_mins       UInt32,
        reason              String,
        impact_units        UInt32,
        is_planned          UInt8
    )
    ENGINE = MergeTree()
    PARTITION BY toYYYYMM(downtime_date)
    ORDER BY (line_id, downtime_date, downtime_id)
    """,

    # ── fact_quality_inspection ───────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.fact_quality_inspection
    (
        inspection_id       String,
        inspection_date     Date,
        inspection_ts       DateTime,
        line_id             String,
        sku_id              String,
        batch_number        String,
        result              String,
        ph_level            Float32,
        brix_level          Float32,
        co2_volume          Float32,
        fill_volume_ml      Float32,
        inspector_id        String,
        comments            Nullable(String)
    )
    ENGINE = MergeTree()
    PARTITION BY toYYYYMM(inspection_date)
    ORDER BY (line_id, inspection_date, inspection_id)
    """,

    # ── fact_clickstream_event ────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_db.fact_clickstream_event
    (
        event_id            String,
        event_timestamp     DateTime,
        event_date          Date,
        session_id          String,
        customer_id         Nullable(String),
        territory_id        String,
        event_type          String,
        page_url            String,
        sku_id              Nullable(String),
        order_id            Nullable(String),
        device_type         String,
        os                  String,
        browser             String,
        ip_address          Nullable(String),
        utm_source          Nullable(String),
        utm_medium          Nullable(String),
        utm_campaign        Nullable(String),
        time_on_page_sec    Nullable(UInt16),
        search_query        Nullable(String),
        pii_flag            UInt8
    )
    ENGINE = MergeTree()
    PARTITION BY toYYYYMM(event_date)
    ORDER BY (event_date, session_id, event_timestamp)
    """,

    # ── Materialized Views ────────────────────────────────────────────

    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mart_db.mv_daily_sales_by_territory
    ENGINE = SummingMergeTree()
    PARTITION BY toYYYYMM(order_date)
    ORDER BY (order_date, territory_id, order_status)
    AS
    SELECT
        order_date,
        territory_id,
        order_status,
        count()                     AS num_orders,
        sum(grand_total_pkr)        AS total_revenue_pkr,
        sum(gst_amount_pkr)         AS total_gst_pkr,
        avg(grand_total_pkr)        AS avg_order_value_pkr
    FROM mart_db.fact_sales_order
    GROUP BY order_date, territory_id, order_status
    """,

    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mart_db.mv_daily_production_summary
    ENGINE = SummingMergeTree()
    PARTITION BY toYYYYMM(run_date)
    ORDER BY (run_date, line_id)
    AS
    SELECT
        run_date,
        line_id,
        count()                     AS num_runs,
        sum(planned_units)          AS total_planned_units,
        sum(actual_units)           AS total_actual_units,
        sum(good_units)             AS total_good_units,
        sum(defective_units)        AS total_defective_units,
        avg(efficiency_pct)         AS avg_efficiency_pct,
        avg(oee_pct)                AS avg_oee_pct
    FROM mart_db.fact_production_run
    GROUP BY run_date, line_id
    """,
]


def apply_schema(host: str = "localhost", port: int = 9000):
    log.info("Connecting to ClickHouse at %s:%d...", host, port)
    client = Client(host=host, port=port)

    # Verify connection
    version = client.execute("SELECT version()")[0][0]
    log.info("Connected. ClickHouse version: %s", version)

    success = 0
    failed = 0
    for stmt in DDL_STATEMENTS:
        name = stmt.strip().split("\n")[0].strip()[:80]
        try:
            client.execute(stmt)
            log.info("  ✓ %s", name)
            success += 1
        except Exception as exc:
            log.error("  ✗ %s\n    Error: %s", name, exc)
            failed += 1

    log.info("")
    log.info("Schema applied: %d succeeded, %d failed.", success, failed)

    if failed == 0:
        log.info("✓ All tables and views created successfully!")
        log.info("")
        log.info("Tables in mart_db:")
        tables = client.execute("SHOW TABLES FROM mart_db")
        for t in tables:
            log.info("  - mart_db.%s", t[0])
    else:
        log.warning("Some statements failed. Check errors above.")

    return failed == 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Apply MyCola ClickHouse schema")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()
    ok = apply_schema(args.host, args.port)
    sys.exit(0 if ok else 1)
