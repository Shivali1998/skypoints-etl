# SkyPoints ETL

SQL-first ELT on Snowflake. SQL does all data work (billions of rows never leave the warehouse);
Python orchestrates, renders per-country SQL from config, generates test data and runs tests.

See `docs/architecture.md`, `docs/data_issues_found.md`, `docs/demo_script.md`, `AI_USAGE.md`.

## Run
```
pip install -r requirements.txt
pytest                                                    # local tests (DuckDB, no Snowflake needed)
python -m src.pipeline.runner --date 20240115 --dry-run   # print rendered SQL
cp .env.example .env  # fill in, export, then:
python -m src.pipeline.runner --date 20240115
```

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
