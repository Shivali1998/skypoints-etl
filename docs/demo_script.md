# Live demo script (~15 min)

## Before the interview
1. Snowflake trial active. Export `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, and `SNOWFLAKE_PASSWORD` or `SNOWFLAKE_TOKEN` (README, "Run").
2. Token logins need a network policy that allows **today's IP**. On a new network run in Snowsight (as ACCOUNTADMIN):
   `ALTER NETWORK POLICY SKYPOINTS_DEMO_POLICY SET ALLOWED_IP_LIST = ('<your public ip>');` (get it with `curl https://api.ipify.org`).
3. Dry run an hour before: `python -m src.pipeline.runner --date 20240115` must print 9 steps and `reconciled`.
4. Optional: pre-run the 1M test (`python scripts/scale_test.py`, ~6 min, mostly upload) so the results are in Snowflake and in `docs/scale_test.md`.
5. Open in tabs: `docs/architecture.md`, `docs/data_issues_found.md`, `AI_USAGE.md`, a Snowsight worksheet, and a terminal in the repo.

## 1. Design (2 min) - `docs/architecture.md`
"SQL-first ELT. Raw is all text so a bad row never fails a load. Everything is typed and validated in SQL inside Snowflake;
rejected rows go to `DQ_REJECTS` with a reason, nothing is dropped. Python only orchestrates, generates per-country SQL from config,
and tests."

## 2. The feeds and what is wrong with them (2 min) - README + `docs/data_issues_found.md`
Key column is Member Name (not unique), 11 spec fields vs 10 in the records, DOB format differs, short member IDs,
mixed country codes, a partner called `SkyPoints`, PENDING transactions.

## 3. Run the sample (3 min)
```
python -m src.pipeline.runner --date 20240115
```
Point at the per-step timings. Then in Snowsight:
```sql
USE DATABASE SKYPOINTS;
SELECT rule_code, business_key, raw_value FROM STAGING.DQ_REJECTS ORDER BY 1;      -- IDs 22345/2256, partner SkyPoints
SELECT member_name, dob, age, stale_member, country_iso3 FROM STAGING.STG_MEMBERS;  -- DOB 03051985 -> 1985-05-03, leading zero kept
SELECT member_id, country_iso3 FROM CURATED.MEMBER_CURRENT;
SELECT 'INDIA' t, member_id FROM CURATED.TABLE_INDIA UNION ALL SELECT 'USA', member_id FROM CURATED.TABLE_USA;
```

## 4. Country move + JSON status change (3 min)
Day 2 moves Ravi (223458) from India to Canada and flips transaction RX10091 to CANCELLED:
```
python -m src.pipeline.runner --date 20240116 --data-dir data/sample/day2
```
```sql
SELECT member_id FROM CURATED.TABLE_INDIA;                       -- empty: Ravi left
SELECT member_id, source_file_date FROM CURATED.TABLE_CANADA WHERE member_id = '223458';
SELECT txn_id, status, member_found FROM CURATED.FCT_REDEMPTIONS ORDER BY 1;   -- RX10091 CANCELLED
SELECT * FROM CURATED.V_MEMBER_REDEMPTIONS;                      -- the join back to members
```
Rerun `--date 20240115` to show it is idempotent and an older file does not overwrite newer data.

## 5. Scale (3 min) - `docs/scale_test.md`
Show the pre-run 1M results and `SELECT step, elapsed_s FROM AUDIT.ETL_RUN_LOG ORDER BY started_ts DESC LIMIT 9;`.
Optionally run live (1-2 min): `python scripts/scale_test.py --rows 100000 --chunks 2 --date 20240120 --id-start 4000000`
(use a fresh date and id-start each time). It prints PASS/FAIL for every count against the generated files.
Be explicit: tested at millions, not billions. For billions: larger warehouse, 100-250 MB chunks, Snowpipe from S3,
cluster on (country, date), possibly one clustered table with per-country views instead of physical tables.

## 6. AI usage (2 min) - `AI_USAGE.md` and `git log --oneline`
Walk through the mistakes you caught and fixed (field count from NULLs, REGEXP_COUNT not allowed in COPY, per-country
full scans, uncompressed upload) and what is and is not verified.

## If something breaks
- Login error "Network policy is required" / "invalid token": update the IP in the policy or use a fresh token.
- Slow upload: run `--data-dir data/sample` (tiny) instead of the generated files.
- Warehouse suspended: it auto-resumes; the first query takes a few seconds.
