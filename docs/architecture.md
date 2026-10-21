# Architecture

SQL-first ELT on Snowflake. SQL does all data work; Python orchestrates, generates per-country SQL from config and tests.

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
│ AUDIT.ETL_RUN_LOG  run_id, step, status, elapsed seconds, error text, per step   │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─ ORCHESTRATION   python -m src.pipeline.runner --date YYYYMMDD ─────────────────────┐
│ Runs the 10 steps in config/pipeline.yaml in order, logs each one, stops at the     │
│ first failure, then checks raw rows == staged rows. Every step is delete-then-      │
│ insert or MERGE, so a rerun of the same date is safe.                               │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## One daily run (`python -m src.pipeline.runner --date YYYYMMDD`)

| # | Step | What it does |
|---|---|---|
| 0 | validate + upload (Python) | Checks file names, dates and the member header record; removes any earlier upload of that date; PUTs gzip chunks |
| 1 | `copy_raw_members` | `COPY INTO RAW_MEMBER_LINES`, then parse each line into `RAW_MEMBERS` (all VARCHAR, with `field_count`) |
| 2 | `copy_raw_redemptions` | `COPY INTO RAW_REDEMPTIONS` (VARIANT) |
| 3 | `load_stg_members` | Typed columns with `TRY_TO_DATE`, `AGE`, `STALE_MEMBER`, `country_iso3` from `REF.COUNTRY` |
| 4 | `dq_members` | 17 rules in one pass, each violation written to `DQ_REJECTS`; staged rows are kept, rejects are excluded downstream |
| 5 | `build_member_current` | Today's valid members (anti-join on rejects), latest record wins, `MERGE` into `MEMBER_CURRENT` |
| 6 | `country_split` | Per country: `MERGE` today's members into `TABLE_<COUNTRY>`, delete today's members who moved elsewhere |
| 7 | `load_stg_redemptions` | `LATERAL FLATTEN` to one row per transaction |
| 8 | `dq_redemptions` | Mandatory fields, miles > 0, status, partner whitelist, txn date <= feed date |
| 9 | `load_fct_redemptions` | Latest feed wins per `txn_id`, `MERGE` into `FCT_REDEMPTIONS`, orphans kept with `member_found = FALSE` |
| 10 | `create_views` | `V_MEMBER_REDEMPTIONS` |
| - | reconcile | raw detail rows must equal staged rows, otherwise the run fails |

## Design decisions
- **RAW is text only.** A bad date or short row never fails a load; it is rejected later with a reason and kept in `DQ_REJECTS`.
- **Incremental and idempotent.** One `file_date` per run; every step is delete-then-insert or `MERGE`. An older file never overwrites newer data.
- **No full-table scans per run.** The country split and the redemption load touch only the day's members and transactions.
- **Country tables come from config.** `REF.COUNTRY` and `config/country_mapping.yaml` drive the `CREATE TABLE` and `MERGE` per country, so a new country is a config row.
  The brief asks for physical tables; at scale one clustered table with per-country views is usually better.
- **Business key is `member_id`.** The spec marks Member Name as the key column, which is not unique.
- **Parallel load.** Large days are split into `_NNN` chunk files; `COPY INTO` loads them in parallel. In production, Snowpipe from S3 replaces the PUT.

## Python and SQL split
| Python | SQL (Snowflake) |
|---|---|
| Runner, step order, run log, reconciliation | All loading, typing, validation, deduplication and merging |
| File checks, gzip upload | `COPY INTO`, `MERGE`, `QUALIFY`, `LATERAL FLATTEN` |
| Per-country SQL rendering from config | |
| Test-data generator, scale test, pytest | |
