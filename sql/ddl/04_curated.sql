CREATE TABLE IF NOT EXISTS CURATED.MEMBER_CURRENT (
  member_id STRING, member_name STRING, enrollment_date DATE, last_flight_date DATE,
  tier_code STRING, agent_name STRING, state STRING, country_iso3 STRING,
  dob DATE, is_active STRING, age NUMBER, stale_member STRING,
  source_file_date DATE, updated_ts TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
) CLUSTER BY (country_iso3);

-- Per-country tables are generated from REF.COUNTRY: see sql/transform/templates/country_table.sql.j2

CREATE TABLE IF NOT EXISTS CURATED.FCT_REDEMPTIONS (
  txn_id STRING, member_id STRING, feed_date DATE, txn_date DATE,
  partner STRING, miles_redeemed NUMBER, status STRING, member_found BOOLEAN
) CLUSTER BY (txn_date);
