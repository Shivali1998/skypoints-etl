CREATE TABLE IF NOT EXISTS AUDIT.ETL_RUN_LOG (
  run_id STRING, file_date DATE, step STRING, status STRING,
  rows_in NUMBER, rows_out NUMBER, rows_rejected NUMBER,
  started_ts TIMESTAMP_NTZ, ended_ts TIMESTAMP_NTZ, message STRING
);
CREATE TABLE IF NOT EXISTS AUDIT.FILE_LOAD_LOG (
  file_name STRING, file_hash STRING, file_date DATE, feed STRING, loaded_ts TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
