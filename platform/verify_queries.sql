-- MyCola Platform — Verification Queries
-- Run these after loading data to confirm the warehouse is working correctly.
-- Execute via: C:\mycola\clickhouse\client.cmd
-- Then paste any query below.

-- ═══════════════════════════════════════════════════════════════
-- 1. ROW COUNT SUMMARY — Quick sanity check
-- ═══════════════════════════════════════════════════════════════
SELECT 'mart_db.dim_customer' AS tbl, count() AS rows FROM mart_db.dim_customer
UNION ALL SELECT 'mart_db.dim_product', count() FROM mart_db.dim_product
UNION ALL SELECT 'mart_db.dim_warehouse', count() FROM mart_db.dim_warehouse
UNION ALL SELECT 'mart_db.dim_territory', count() FROM mart_db.dim_territory
UNION ALL SELECT 'mart_db.dim_sales_rep', count() FROM mart_db.dim_sales_rep
UNION ALL SELECT 'mart_db.dim_supplier', count() FROM mart_db.dim_supplier
UNION ALL SELECT 'mart_db.fact_sales_order', count() FROM mart_db.fact_sales_order
UNION ALL SELECT 'mart_db.fact_sales_order_line', count() FROM mart_db.fact_sales_order_line
UNION ALL SELECT 'mart_db.fact_inventory_movement', count() FROM mart_db.fact_inventory_movement
UNION ALL SELECT 'mart_db.fact_gl_entry', count() FROM mart_db.fact_gl_entry
UNION ALL SELECT 'mart_db.fact_production_run', count() FROM mart_db.fact_production_run
UNION ALL SELECT 'mart_db.fact_clickstream_event', count() FROM mart_db.fact_clickstream_event
ORDER BY rows DESC;

-- ═══════════════════════════════════════════════════════════════
-- 2. SALES DASHBOARD — Monthly revenue by territory
-- ═══════════════════════════════════════════════════════════════
SELECT
    toYear(order_date)          AS year,
    toMonth(order_date)         AS month,
    territory_id,
    count()                     AS num_orders,
    round(sum(grand_total_pkr) / 1e6, 2)  AS revenue_million_pkr,
    round(avg(grand_total_pkr), 0)         AS avg_order_pkr
FROM mart_db.fact_sales_order
WHERE order_status IN ('Confirmed', 'Completed')
GROUP BY year, month, territory_id
ORDER BY year DESC, month DESC, revenue_million_pkr DESC
LIMIT 30;

-- ═══════════════════════════════════════════════════════════════
-- 3. TOP 10 SKUs BY REVENUE
-- ═══════════════════════════════════════════════════════════════
SELECT
    l.sku_id,
    p.sku_name,
    p.category,
    count()                                 AS num_line_items,
    sum(l.quantity)                         AS total_units_sold,
    round(sum(l.line_total_pkr) / 1e6, 2)  AS revenue_million_pkr,
    round(avg(l.discount_pct), 1)           AS avg_discount_pct
FROM mart_db.fact_sales_order_line l
LEFT JOIN mart_db.dim_product p ON l.sku_id = p.sku_id
GROUP BY l.sku_id, p.sku_name, p.category
ORDER BY revenue_million_pkr DESC
LIMIT 10;

-- ═══════════════════════════════════════════════════════════════
-- 4. INVENTORY — Current stock levels (latest closing_stock per SKU/WH)
-- ═══════════════════════════════════════════════════════════════
SELECT
    m.sku_id,
    p.sku_name,
    m.warehouse_id,
    w.warehouse_name,
    m.closing_stock,
    CASE WHEN m.closing_stock < 1000 THEN '⚠ REORDER' ELSE '✓ OK' END AS stock_status
FROM (
    SELECT
        sku_id,
        warehouse_id,
        argMax(closing_stock, movement_date) AS closing_stock
    FROM mart_db.fact_inventory_movement
    GROUP BY sku_id, warehouse_id
) m
LEFT JOIN mart_db.dim_product p ON m.sku_id = p.sku_id
LEFT JOIN mart_db.dim_warehouse w ON m.warehouse_id = w.warehouse_id
ORDER BY closing_stock ASC
LIMIT 30;

-- ═══════════════════════════════════════════════════════════════
-- 5. P&L SUMMARY — Revenue vs Expense by month (simplified)
-- ═══════════════════════════════════════════════════════════════
SELECT
    toStartOfMonth(transaction_date)    AS month,
    account_type,
    round(sum(amount_pkr) / 1e6, 2)    AS total_million_pkr
FROM mart_db.fact_gl_entry
WHERE account_type IN ('Revenue', 'Expense')
GROUP BY month, account_type
ORDER BY month DESC, account_type;

-- ═══════════════════════════════════════════════════════════════
-- 6. PRODUCTION — OEE and efficiency by line
-- ═══════════════════════════════════════════════════════════════
SELECT
    line_id,
    line_name,
    count()                         AS total_runs,
    round(avg(efficiency_pct), 1)   AS avg_efficiency_pct,
    round(avg(oee_pct), 1)          AS avg_oee_pct,
    round(avg(defect_rate_pct), 2)  AS avg_defect_rate_pct,
    sum(good_units)                 AS total_good_units,
    sum(defective_units)            AS total_defective_units
FROM mart_db.fact_production_run
GROUP BY line_id, line_name
ORDER BY avg_oee_pct DESC;

-- ═══════════════════════════════════════════════════════════════
-- 7. CLICKSTREAM — Top event types and conversion funnel
-- ═══════════════════════════════════════════════════════════════
SELECT
    event_type,
    count()                                 AS event_count,
    round(100.0 * count() / sum(count()) OVER (), 1) AS pct
FROM mart_db.fact_clickstream_event
GROUP BY event_type
ORDER BY event_count DESC;

-- Cart-to-order conversion
SELECT
    countIf(event_type = 'add_to_cart')    AS add_to_cart,
    countIf(event_type = 'checkout_start') AS checkout_start,
    countIf(event_type = 'order_placed')   AS orders_placed,
    round(100.0 * countIf(event_type = 'order_placed') / nullIf(countIf(event_type = 'add_to_cart'), 0), 1) AS conversion_rate_pct
FROM mart_db.fact_clickstream_event;

-- ═══════════════════════════════════════════════════════════════
-- 8. MATERIALIZED VIEW — Performance test
-- ═══════════════════════════════════════════════════════════════
-- This should return in milliseconds (pre-aggregated)
SELECT *
FROM mart_db.mv_daily_sales_by_territory
ORDER BY order_date DESC, total_revenue_pkr DESC
LIMIT 20;

-- ═══════════════════════════════════════════════════════════════
-- 9. SALES REP PERFORMANCE REPORT
-- ═══════════════════════════════════════════════════════════════
SELECT
    o.sales_rep_id,
    r.rep_name,
    r.territory_id,
    count()                                     AS num_orders,
    round(sum(o.grand_total_pkr) / 1e6, 2)     AS revenue_million_pkr,
    round(r.monthly_target_pkr * 12 / 1e6, 2)  AS annual_target_million_pkr,
    round(
        100.0 * sum(o.grand_total_pkr) / nullIf(r.monthly_target_pkr * 12, 0),
        1
    )                                           AS target_achievement_pct
FROM mart_db.fact_sales_order o
LEFT JOIN mart_db.dim_sales_rep r ON o.sales_rep_id = r.rep_id
WHERE order_status IN ('Confirmed', 'Completed')
GROUP BY o.sales_rep_id, r.rep_name, r.territory_id, r.monthly_target_pkr
ORDER BY revenue_million_pkr DESC
LIMIT 20;

-- ═══════════════════════════════════════════════════════════════
-- 10. DATA QUALITY CHECK — Detect schema deviation records
-- ═══════════════════════════════════════════════════════════════
-- Orders missing a customer_id (NULL injection check)
SELECT
    'fact_sales_order'   AS table_name,
    'customer_id IS NULL' AS check_name,
    countIf(customer_id IS NULL) AS failed_rows,
    count() AS total_rows,
    round(100.0 * countIf(customer_id IS NULL) / count(), 2) AS null_rate_pct
FROM mart_db.fact_sales_order;
