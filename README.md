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
