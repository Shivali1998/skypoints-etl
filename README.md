# SkyPoints ETL

SQL-first ELT on Snowflake. SQL does all data work (billions of rows never leave the warehouse);
Python orchestrates, renders per-country SQL from config, generates test data and runs tests.

See `docs/architecture.md`, `docs/data_issues_found.md`, `docs/demo_script.md`, `AI_USAGE.md`.

## Run
```
pip install -r requirements.txt
pytest                                                    # 25 local tests (DuckDB, no Snowflake needed)
python -m src.pipeline.runner --date 20240115 --dry-run   # print the rendered SQL, no connection
```
Against Snowflake (creates the `SKYPOINTS` database, schemas, stage, tables and an XSMALL warehouse on first run):
```
export SNOWFLAKE_ACCOUNT=<org-account> SNOWFLAKE_USER=<login name>
export SNOWFLAKE_PASSWORD=...            # or, if the account is SSO-only / MFA:
export SNOWFLAKE_TOKEN=...               # programmatic access token
python -m src.pipeline.runner --date 20240115 [--data-dir data/sample]
```
Notes from setting this up on a trial account:
- Token (PAT) logins require a network policy on the user, e.g.
  `CREATE NETWORK POLICY p ALLOWED_IP_LIST=('<your ip>'); ALTER USER "<user>" SET NETWORK_POLICY=p;`
- The connector wants the **login name** (often the email); `ALTER USER` wants the **user name** (case-sensitive when quoted).
- Input files are `members_<YYYYMMDD>[_NNN].dat` and `redemptions_<YYYYMMDD>[_NNN].json`; every chunk of a day loads in parallel.

Generate demo data: `python -m src.datagen.generate --rows 1000000 --chunks 4 --bad-pct 2 --date 20240118 --id-start 2000000`

## Scale test (measured, Snowflake trial, XSMALL warehouse)

1,000,000 members + 1,999,603 redemption transactions (2% deliberately bad rows), split into 4 chunk files per feed, gzip-compressed:

| Step | Seconds |
|---|---|
| copy_raw_members (4 chunks, parallel COPY) | 5.2 |
| copy_raw_redemptions | 4.4 |
| load_stg_members (cast + AGE + STALE_MEMBER) | 2.4 |
| dq_members (17 rules, one pass) | 2.0 |
| build_member_current (latest wins + MERGE) | 3.6 |
| country_split (5 tables, only today's members) | 8.9 |
| load_stg_redemptions (FLATTEN) | 3.7 |
| dq_redemptions | 1.1 |
| load_fct_redemptions | 1.7 |
| **Pipeline steps total** | **~33** |
| Upload from my laptop (not part of the pipeline) | ~5 min |

Correctness at this volume (checked against the generated files, not just "no errors"):
- Every planted defect was rejected, with counts equal to the file: BAD_DOB 2,914, BAD_MEMBER_ID_FORMAT 2,883, BAD_TIER 2,820, FIELD_COUNT_MISMATCH 2,809, FLIGHT_BEFORE_ENROLLMENT 2,863, MISSING_MANDATORY 2,885, UNMAPPED_COUNTRY 2,884, BAD_MILES 20,058.
- 1,000,000 raw = 1,000,000 staged; 979,942 valid members in MEMBER_CURRENT (= 1,000,000 - 20,058).
- 1,979,545 transactions loaded (= 1,999,603 - 20,058 rejected).
- Each member sits in exactly one country table (980,892 rows, 980,892 distinct ids, incl. earlier test days).
- 102 extra `DUP_MEMBER_IN_FILE` rejects are a generator artefact: its "short id" defect picks random ids from 1-9999, which collide within a chunk. Those rows are rejected for their format anyway.

Honest limits: this is millions, not billions. Step times are for an XSMALL warehouse and one day; I have not
measured how they scale, so I would size the warehouse (and chunk files to ~100-250 MB) from a larger test, and use
Snowpipe/auto-ingest from S3 instead of PUT from a laptop. Two changes were made because of this test:
the country split now only touches the members in the day's file, and the DQ rules evaluate all checks in a single
pass instead of scanning the data once per rule.

## Deliverables map
| # | Deliverable | Where |
|---|---|---|
| 1 | DDL raw / staging / country tables | `sql/ddl/`, `sql/transform/templates/country_table.sql.j2` |
| 2 | Staging with AGE, STALE_MEMBER | `sql/transform/load_stg_members.sql`, `sql/macros/derived.sql.j2` |
| 3 | Per-country split, latest record wins | `build_member_current.sql`, `country_merge.sql.j2` |
| 4 | JSON flatten + join | `load_stg_redemptions.sql`, `load_fct_redemptions.sql`, `v_member_redemptions.sql` |
| 5 | Validations | `sql/dq/`, `src/ingest/file_checks.py` |
| 6 | Demo | `docs/demo_script.md`, `src/datagen/generate.py` |

## Assumptions to confirm
DOB is DDMMYYYY; member_id is 6–18 digits; partner whitelist and tier/status lists in `config/`.
Per-country physical tables are required by the brief; at scale one clustered table + views is usually better.
