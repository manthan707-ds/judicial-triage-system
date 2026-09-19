import duckdb

BASE = r"C:\Users\manth\SIH PROJECT\DATA\justice_data\csv"
CASES_FILE = BASE + r"\cases\cases_2018.csv"
TYPE_KEY_FILE = BASE + r"\keys\type_name_key.csv"
PURPOSE_KEY_FILE = BASE + r"\keys\purpose_name_key.csv"
OUTPUT_FILE = r"C:\Users\manth\SIH PROJECT\karnataka_2018_clean.csv"

STATE_CODE = "03"  # Karnataka

con = duckdb.connect()

query = f"""
COPY (
    WITH cases AS (
        SELECT *
        FROM read_csv_auto('{CASES_FILE}', ignore_errors=true, ALL_VARCHAR=true)
        WHERE state_code = '{STATE_CODE}'
    ),
    type_key AS (
        SELECT DISTINCT
            CAST(year AS VARCHAR) AS year,
            CAST(type_name AS VARCHAR) AS type_name,
            type_name_s
        FROM read_csv_auto('{TYPE_KEY_FILE}', ignore_errors=true, ALL_VARCHAR=true)
    ),
    purpose_key AS (
        SELECT DISTINCT
            CAST(year AS VARCHAR) AS year,
            CAST(purpose_name AS VARCHAR) AS purpose_name,
            purpose_name_s
        FROM read_csv_auto('{PURPOSE_KEY_FILE}', ignore_errors=true, ALL_VARCHAR=true)
    ),
    cleaned AS (
        SELECT
            c.ddl_case_id,
            c.year,
            c.state_code,
            c.dist_code,
            c.court_no,
            c.judge_position,
            CASE WHEN c.type_name IN ('-9998','-9999') THEN NULL ELSE c.type_name END AS type_name_code,
            tk.type_name_s AS type_name_label,
            CASE WHEN c.purpose_name IN ('-9998','-9999') THEN NULL ELSE c.purpose_name END AS purpose_name_code,
            pk.purpose_name_s AS purpose_name_label,
            TRY_CAST(c.date_of_filing AS DATE) AS date_of_filing,
            TRY_CAST(NULLIF(c.date_of_decision, '') AS DATE) AS date_of_decision
        FROM cases c
        LEFT JOIN type_key tk
            ON c.year = tk.year AND c.type_name = tk.type_name
        LEFT JOIN purpose_key pk
            ON c.year = pk.year AND c.purpose_name = pk.purpose_name
    ),
    with_target AS (
        SELECT
            *,
            CASE WHEN date_of_decision IS NOT NULL
                 THEN DATE_DIFF('day', date_of_filing, date_of_decision)
                 ELSE NULL END AS resolution_days,
            CASE WHEN date_of_decision IS NULL THEN 1 ELSE 0 END AS is_pending,
            CASE WHEN date_of_decision IS NULL
                 THEN DATE_DIFF('day', date_of_filing, CURRENT_DATE)
                 ELSE NULL END AS days_pending_so_far
        FROM cleaned
    )
    SELECT
        *,
        CASE
            WHEN resolution_days IS NULL THEN NULL
            WHEN resolution_days < 90 THEN 'Fast-track'
            WHEN resolution_days < 365 THEN 'Standard'
            ELSE 'Complex'
        END AS triage_bucket
    FROM with_target
    WHERE date_of_filing IS NOT NULL
) TO '{OUTPUT_FILE}' (HEADER, DELIMITER ',');
"""

con.execute(query)

summary = con.execute(f"""
    SELECT
        COUNT(*) AS total_rows,
        SUM(is_pending) AS pending_cases,
        COUNT(triage_bucket) AS labeled_cases,
        SUM(CASE WHEN triage_bucket = 'Fast-track' THEN 1 ELSE 0 END) AS fast_track,
        SUM(CASE WHEN triage_bucket = 'Standard' THEN 1 ELSE 0 END) AS standard,
        SUM(CASE WHEN triage_bucket = 'Complex' THEN 1 ELSE 0 END) AS complex
    FROM read_csv_auto('{OUTPUT_FILE}', ALL_VARCHAR=true)
""").fetchdf()

print(f"\nSaved clean dataset to: {OUTPUT_FILE}\n")
print(summary.to_string(index=False))
