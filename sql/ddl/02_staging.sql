CREATE TABLE IF NOT EXISTS STAGING.STG_MEMBERS (
  file_name STRING, row_no NUMBER, file_date DATE,
  member_name STRING, member_id STRING, enrollment_date DATE, last_flight_date DATE,
  tier_code STRING, agent_name STRING, state STRING, country_src STRING,
  country_iso3 STRING, dob DATE, is_active STRING,
  age NUMBER, stale_member STRING, load_ts TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
) CLUSTER BY (file_date);

CREATE TABLE IF NOT EXISTS STAGING.STG_REDEMPTIONS (
  file_name STRING, file_date DATE, member_id STRING, feed_date DATE,
  txn_id STRING, txn_date DATE, partner STRING, miles_redeemed NUMBER, status STRING,
  load_ts TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
) CLUSTER BY (file_date);

CREATE TABLE IF NOT EXISTS STAGING.DQ_REJECTS (
  feed STRING, file_date DATE, file_name STRING, row_no NUMBER, business_key STRING,
  rule_code STRING, reason STRING, raw_value STRING, load_ts TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
