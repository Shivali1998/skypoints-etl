-- One row per pipeline step per run: what ran, whether it worked, how long it took.
CREATE TABLE IF NOT EXISTS AUDIT.ETL_RUN_LOG (
  run_id STRING, file_date DATE, step STRING, status STRING,
  elapsed_s NUMBER(10,2), message STRING, logged_ts TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
