-- Staging: Inventory Movements

SELECT
    movement_id,
    toDate(movement_date)           AS movement_date,
    toDateTime(movement_ts)         AS movement_ts,
    sku_id,
    sku_name,
    warehouse_id,
    movement_type,
    toInt32(quantity)               AS quantity,
    toInt32(closing_stock)          AS closing_stock,
    toFloat32(unit_cost_pkr)        AS unit_cost_pkr,
    toFloat32(total_cost_pkr)       AS total_cost_pkr,
    supplier_id,
    reference_doc,
    toUInt8(is_reconciled)          AS is_reconciled

FROM mart_db.fact_inventory_movement
WHERE movement_id IS NOT NULL
