-- Mart: Production Efficiency by Line and Month

{{ config(
    materialized = 'table',
    engine = 'MergeTree()',
    order_by = '(run_year, run_month, line_id)'
) }}

SELECT
    toYear(run_date)                AS run_year,
    toMonth(run_date)               AS run_month,
    toStartOfMonth(run_date)        AS run_month_start,
    line_id,
    line_name,
    count()                         AS total_runs,
    sum(planned_units)              AS total_planned_units,
    sum(actual_units)               AS total_actual_units,
    sum(good_units)                 AS total_good_units,
    sum(defective_units)            AS total_defective_units,
    avg(efficiency_pct)             AS avg_efficiency_pct,
    avg(oee_pct)                    AS avg_oee_pct,
    avg(defect_rate_pct)            AS avg_defect_rate_pct,
    sum(run_hours)                  AS total_run_hours

FROM {{ ref('stg_production') }}
GROUP BY run_year, run_month, run_month_start, line_id, line_name
ORDER BY run_year, run_month, avg_oee_pct DESC
