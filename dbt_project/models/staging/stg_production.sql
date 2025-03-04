-- Staging: Production Runs

SELECT
    run_id,
    toDate(run_date)                AS run_date,
    line_id,
    line_name,
    sku_id,
    sku_name,
    shift,
    toDateTime(start_ts)            AS start_ts,
    toDateTime(end_ts)              AS end_ts,
    toFloat32(run_hours)            AS run_hours,
    toUInt32(planned_units)         AS planned_units,
    toUInt32(actual_units)          AS actual_units,
    toUInt32(defective_units)       AS defective_units,
    toUInt32(good_units)            AS good_units,
    toFloat32(efficiency_pct)       AS efficiency_pct,
    toFloat32(defect_rate_pct)      AS defect_rate_pct,
    toFloat32(oee_pct)              AS oee_pct,
    operator_id,
    batch_number

FROM mart_db.fact_production_run
WHERE run_id IS NOT NULL
