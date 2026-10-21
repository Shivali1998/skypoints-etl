# SkyPoints ETL

Daily load of an airline loyalty programme's members into **per-country tables** on Snowflake, plus a
semi-structured **redemption feed**, built to run on millions of rows per day.

**SQL-first ELT.** All data work happens as set-based SQL inside Snowflake, so rows never pass through Python.
Python orchestrates the steps, renders per-country SQL from config, generates test data and runs tests.

## Architecture

```
┌─ SOURCE (daily) ────────────────────────────────────────────────────────────────────┐
│ members_YYYYMMDD[_NNN].dat        pipe-delimited, 1 header + 1 detail row per member│
│ redemptions_YYYYMMDD[_NNN].json   1 JSON document per member, nested transactions   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼ PYTHON: check name/date + header, clear old upload, gzip + PUT
┌─ STAGE   @RAW.SKYPOINTS_STAGE ──────────────────────────────────────────────────────┐
│ gzip chunks (100-250 MB each at scale), loaded in parallel by COPY INTO             │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼ SQL: COPY INTO (whole line / VARIANT), then parse
┌─ RAW   nothing is typed, so a bad value can never fail a load ──────────────────────┐
│ RAW_MEMBER_LINES   untouched source lines                                           │
│ RAW_MEMBERS        parsed columns, all VARCHAR + file_name, row_no, field_count     │
│ RAW_REDEMPTIONS    one VARIANT document per row                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼ SQL: TRY_TO_* typing, AGE, STALE_MEMBER, country lookup, FLATTEN
┌─ STAGING ───────────────────────────────────────────────────────────────────────────┐
│ STG_MEMBERS        typed rows + age + stale_member + country_iso3 (REF.COUNTRY)     │
│ STG_REDEMPTIONS    one row per transaction                                          │
│ DQ_REJECTS         one row per violated rule: file, row, key, rule, reason, value   │
│                    (17 member + 5 redemption rules, evaluated in one pass)          │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼ SQL: anti-join on DQ_REJECTS, latest record wins (QUALIFY), MERGE
┌─ CURATED ───────────────────────────────────────────────────────────────────────────┐
│ MEMBER_LATEST      today's valid members, one row per member (transient)            │
│ MEMBER_CURRENT     one row per member across all days                               │
│ TABLE_USA  TABLE_INDIA  TABLE_PHILIPPINES  TABLE_CANADA  TABLE_AUSTRALIA            │
│                    MERGE only today's members; delete those that moved country      │
│ FCT_REDEMPTIONS    latest feed wins per txn_id; unknown members kept                │
│                    (member_found = FALSE)                                           │
│ V_MEMBER_REDEMPTIONS   members LEFT JOIN redemptions on member_id                   │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─ SUPPORTING ────────────────────────────────────────────────────────────────────────┐
│ REF.COUNTRY        source code (USA, US, PHIL, AU ...) -> ISO-3 -> country table    │
│ AUDIT.ETL_RUN_LOG  run_id, step, status, elapsed seconds, error text, per step      │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─ ORCHESTRATION   python -m src.pipeline.runner --date YYYYMMDD ─────────────────────┐
│ Runs the 10 steps in config/pipeline.yaml in order, logs each one, stops at the     │
│ first failure, then checks raw rows == staged rows. Every step is delete-then-      │
│ insert or MERGE, so a rerun of the same date is safe.                               │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

| Layer | Responsibility |
|---|---|
| **RAW** | Everything stored as text with file name and row number; the member file is landed as raw lines first so each row's field count can be checked. |
| **STAGING** | Typed columns, `AGE` (corrected for birthdays not yet reached) and `STALE_MEMBER` (> 90 days since last flight). Rule violations go to `DQ_REJECTS`; rows are never dropped silently. |
| **CURATED** | `MEMBER_CURRENT` keeps the latest record per member; each country table is merged from it, and a member who moves country is deleted from the old table. |
| **Redemptions** | One row per transaction, the latest feed wins per `txn_id` (PENDING becomes COMPLETED); unknown members are kept with `member_found = FALSE`. |

**Design decisions**
- **Incremental and idempotent:** each run handles one `file_date`; every step is delete-then-insert or `MERGE`, so a rerun is safe and an older file never overwrites newer data.
- **Country tables are generated from `REF.COUNTRY` and config:** a new country is a config row, not new SQL. The split touches only the members in the day's file, not the whole table.
- **Validation in one pass:** 17 member rules and 5 redemption rules are evaluated together and flattened once.
- **Chunked parallel load:** large days are split into `_NNN` files (aim for 100-250 MB each) and loaded in parallel.
- **Business key is `member_id`**, not Member Name.

## Input feeds

**Members**: `members_<YYYYMMDD>[_NNN].dat`, pipe-delimited, one header and one detail record per member.
```
|H|Member_Name|Member_Id|Enrollment_Date|Last_Flight_Date|Tier_Code|Agent_Name|State|Country|DOB|Is_Active
|D|Elena|223457|20101012|20121013|GLD|Sam|CA|USA|03051985|A
```

**Redemptions**: `redemptions_<YYYYMMDD>[_NNN].json`, one JSON document per member.
```json
{ "member_id": "223457", "feed_date": "20240115", "redemptions": [
  { "txn_id": "RX10091", "txn_date": "20240110", "partner": "AeroLink", "miles_redeemed": 12000, "status": "COMPLETED" } ] }
```
Column lengths, types and rules: `config/member_file_spec.yaml`, `config/redemption_spec.yaml`.
Problems found in the sample data and how each is handled: `docs/data_issues_found.md`.

## What was built

| Deliverable | Where |
|---|---|
| 1. DDL for raw, staging and country tables | `sql/ddl/`, `sql/transform/templates/country_table.sql.j2` |
| 2. Staging with `AGE` and `STALE_MEMBER` | `sql/transform/load_stg_members.sql`, `sql/macros/derived.sql.j2` |
| 3. Per-country split, latest record wins | `build_member_current.sql`, `country_merge.sql.j2` |
| 4. JSON flatten and join to members | `load_stg_redemptions.sql`, `load_fct_redemptions.sql`, `sql/views/v_member_redemptions.sql` |
| 5. Validations | `sql/dq/`, `src/ingest/file_checks.py` |
| 6. Live demonstration | `docs/demo_script.md`, `scripts/scale_test.py` |

**How it was developed:** scaffold and config, then architecture docs, DDL, load and staging, DQ rules, curated transforms,
the Python runner, a data generator, and tests. It was then run on a real Snowflake account, which found and fixed load
issues; scale-reviewed (country split made incremental, DQ made single-pass); extended with chunked parallel loading and
per-step timing; and finally tested at 1,000,000 members.

## How to execute

**1. Set up and run the local tests** (no Snowflake needed; uses DuckDB for the pure-SQL logic)
```
pip install -r requirements.txt
pytest                                                     # 26 tests
python -m src.pipeline.runner --date 20240115 --dry-run    # print the rendered SQL for every step
```

**2. Connect to Snowflake**
```
export SNOWFLAKE_ACCOUNT=<org-account>  SNOWFLAKE_USER=<login name>
export SNOWFLAKE_PASSWORD=...        # or, for SSO/MFA accounts:  export SNOWFLAKE_TOKEN=<programmatic access token>
```
Token logins need a network policy on the user:
`CREATE NETWORK POLICY p ALLOWED_IP_LIST=('<your ip>'); ALTER USER "<user name>" SET NETWORK_POLICY=p;`
(the connector takes the *login name*; `ALTER USER` takes the quoted, case-sensitive *user name*).

**3. Run the pipeline.** The first run creates the `SKYPOINTS` database, schemas, stage, tables and an XSMALL warehouse.
```
python -m src.pipeline.runner --date 20240115                                  # day 1: the sample files in data/sample
python -m src.pipeline.runner --date 20240116 --data-dir data/sample/day2      # day 2: a member moves India -> Canada
```
Each step prints its status and seconds, and ends with a raw-vs-staged reconciliation. Then inspect:
```sql
SELECT rule_code, business_key, raw_value FROM SKYPOINTS.STAGING.DQ_REJECTS;
SELECT * FROM SKYPOINTS.CURATED.TABLE_CANADA;
SELECT * FROM SKYPOINTS.CURATED.V_MEMBER_REDEMPTIONS;
SELECT step, status, elapsed_s FROM SKYPOINTS.AUDIT.ETL_RUN_LOG ORDER BY started_ts DESC;
```

**4. Generate data and run the scale test**
```
python -m src.datagen.generate --rows 100000 --chunks 2 --bad-pct 2 --date 20240120 --id-start 4000000 --out data/generated
python scripts/scale_test.py --rows 1000000 --chunks 4 --date 20240118 --id-start 2000000
```
`scale_test.py` generates the feeds, runs the pipeline, and checks every count against what is in the files
(exits non-zero on any mismatch). Use a fresh `--date` and `--id-start` for each run.

## Results

| Test | Outcome |
|---|---|
| Spec sample (5 members, 2 transactions) | Short IDs `22345` and `2256` and the `SkyPoints` partner rejected; DOB `03051985` becomes 1985-05-03; members land in the right country tables |
| Country move and status change across days | Member leaves `TABLE_INDIA` and appears only in `TABLE_CANADA`; `RX10091` goes COMPLETED to CANCELLED; reruns are idempotent |
| 1,000 rows with 5% planted defects | Every rule's reject count matched the file |
| **1,000,000 members + 1,999,603 transactions** (XSMALL warehouse) | Pipeline steps ~33 s in total; all planted defects rejected with exact counts; 979,942 valid members; no member in two tables |

This is millions, not billions. For billions: size the warehouse and chunk files (100-250 MB) from a larger test,
ingest with Snowpipe from S3 instead of uploading from a laptop, and consider one clustered table with per-country views.
Details and per-step timings: `docs/scale_test.md`.

## Project layout
```
config/    pipeline steps, file specs, country mapping        sql/ddl, load, transform, dq, views, macros
src/       pipeline (runner, country_splitter), ingest, db, datagen
scripts/   scale_test.py                                       tests/    26 pytest tests
docs/      architecture, data issues + assumptions, demo script, scale test results
```
Other docs: `docs/architecture.md`, `docs/demo_script.md`, `AI_USAGE.md`.
