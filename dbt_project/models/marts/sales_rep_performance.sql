-- Mart: Sales Rep Performance Summary

{{ config(
    materialized = 'table',
    engine = 'MergeTree()',
    order_by = '(order_year, order_month, sales_rep_id)'
) }}

SELECT
    order_year,
    order_month,
    sales_rep_id,
    rep_name,
    territory_id,
    count()                                                     AS total_orders,
    countIf(order_status = 'Confirmed')                         AS confirmed_orders,
    sumIf(grand_total_pkr, order_status = 'Confirmed')          AS confirmed_revenue_pkr,
    avg(grand_total_pkr)                                        AS avg_order_value_pkr,
    sum(num_lines)                                              AS total_order_lines

FROM {{ ref('stg_sales_orders') }}
GROUP BY order_year, order_month, sales_rep_id, rep_name, territory_id
ORDER BY order_year, order_month, confirmed_revenue_pkr DESC
