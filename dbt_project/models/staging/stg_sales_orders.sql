-- Staging: Sales Orders
-- Cleans and types the raw fact_sales_order table

SELECT
    order_id,
    toDate(order_date)                          AS order_date,
    toDateTime(order_timestamp)                 AS order_timestamp,
    customer_id,
    customer_name,
    sales_rep_id,
    rep_name,
    territory_id,
    warehouse_id,
    order_status,
    toUInt16(num_lines)                         AS num_lines,
    toFloat32(total_amount_pkr)                 AS total_amount_pkr,
    toFloat32(gst_amount_pkr)                   AS gst_amount_pkr,
    toFloat32(grand_total_pkr)                  AS grand_total_pkr,
    toUInt16(payment_terms_days)                AS payment_terms_days,
    toYear(order_date)                          AS order_year,
    toMonth(order_date)                         AS order_month,
    toStartOfMonth(order_date)                  AS order_month_start

FROM mart_db.fact_sales_order
WHERE order_id IS NOT NULL
