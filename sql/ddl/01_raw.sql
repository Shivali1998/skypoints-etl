-- Everything VARCHAR: a bad value must never fail the load.
CREATE TABLE IF NOT EXISTS RAW.RAW_MEMBERS (
  file_name STRING, row_no NUMBER, file_date DATE, load_ts TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  rec_type STRING, member_name STRING, member_id STRING, enrollment_date STRING,
  last_flight_date STRING, tier_code STRING, agent_name STRING, state STRING,
  country STRING, dob STRING, is_active STRING, field_count NUMBER
) CLUSTER BY (file_date);

CREATE TABLE IF NOT EXISTS RAW.RAW_REDEMPTIONS (
  file_name STRING, row_no NUMBER, file_date DATE,
  load_ts TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), v VARIANT
) CLUSTER BY (file_date);

-- Untouched source lines: COPY transformations can't count delimiters, so parsing happens in INSERT..SELECT.
CREATE TABLE IF NOT EXISTS RAW.RAW_MEMBER_LINES (
  file_name STRING, row_no NUMBER, file_date DATE, line STRING
) CLUSTER BY (file_date);
