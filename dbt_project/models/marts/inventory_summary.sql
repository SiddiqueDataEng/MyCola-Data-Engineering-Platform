-- Mart: Current Inventory Position by SKU and Warehouse

{{ config(
    materialized = 'table',
    engine = 'MergeTree()',
    order_by = '(warehouse_id, sku_id)'
) }}

SELECT
    warehouse_id,
    sku_id,
    sku_name,
    -- Most recent closing stock per SKU/warehouse
    argMax(closing_stock, movement_date)    AS current_stock,
    max(movement_date)                      AS last_movement_date,
    count()                                 AS total_movements,
    sumIf(quantity, quantity > 0)           AS total_inbound,
    abs(sumIf(quantity, quantity < 0))      AS total_outbound,
    avg(unit_cost_pkr)                      AS avg_unit_cost_pkr,
    sum(total_cost_pkr)                     AS total_cost_pkr

FROM {{ ref('stg_inventory') }}
GROUP BY warehouse_id, sku_id, sku_name
