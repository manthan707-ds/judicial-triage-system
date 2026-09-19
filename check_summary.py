import duckdb

OUTPUT_FILE = r"C:\Users\manth\SIH PROJECT\karnataka_2018_clean.csv"
con = duckdb.connect()

summary = con.execute(f"""
    SELECT
        COUNT(*) AS total_rows,
        SUM(CAST(is_pending AS INTEGER)) AS pending_cases,
        COUNT(triage_bucket) AS labeled_cases,
        SUM(CASE WHEN triage_bucket = 'Fast-track' THEN 1 ELSE 0 END) AS fast_track,
        SUM(CASE WHEN triage_bucket = 'Standard' THEN 1 ELSE 0 END) AS standard,
        SUM(CASE WHEN triage_bucket = 'Complex' THEN 1 ELSE 0 END) AS complex
    FROM read_csv(
        '{OUTPUT_FILE}',
        all_varchar=true,
        quote='"',
        escape='"',
        delim=',',
        header=true,
        ignore_errors=true
    )
""").fetchdf()

print(summary.to_string(index=False))
