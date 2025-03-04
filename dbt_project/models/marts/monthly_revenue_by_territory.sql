-- Mart: Monthly Revenue by Territory
-- Pre-aggregated for dashboard use

{{ config(
    materialized = 'table',
    engine = 'MergeTree()',
    order_by = '(order_month_start, territory_id)'
) }}

SELECT
    order_month_start,
    territory_id,
    countIf(order_status = 'Confirmed')                     AS confirmed_orders,
    countIf(order_status = 'Pending')                       AS pending_orders,
    count()                                                 AS total_orders,
    sumIf(grand_total_pkr, order_status = 'Confirmed')      AS confirmed_revenue_pkr,
    sum(grand_total_pkr)                                    AS total_revenue_pkr,
    avg(grand_total_pkr)                                    AS avg_order_value_pkr,
    sum(gst_amount_pkr)                                     AS total_gst_pkr

FROM {{ ref('stg_sales_orders') }}
GROUP BY order_month_start, territory_id
ORDER BY order_month_start DESC, confirmed_revenue_pkr DESC
