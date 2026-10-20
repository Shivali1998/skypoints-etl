# Architecture

```
members_YYYYMMDD.dat ─┐                       RAW        RAW_MEMBERS (all VARCHAR + file_name,row_no,load_ts)
                      ├─► @SKYPOINTS_STAGE ─► COPY INTO  RAW_REDEMPTIONS (VARIANT)
redemptions_*.json ───┘   (100–250 MB chunks)     │
                                                  ▼
                                        STAGING   STG_MEMBERS (typed, AGE, STALE_MEMBER)
                                                  STG_REDEMPTIONS (LATERAL FLATTEN, deduped)
                                                  DQ_REJECTS (file,row,rule,reason)  ← bad rows land here
                                                  │ latest-record-wins (QUALIFY) + MERGE
                                                  ▼
                                        CURATED   MEMBER_CURRENT, TABLE_<COUNTRY>..., FCT_REDEMPTIONS,
                                                  V_MEMBER_REDEMPTIONS
                                        AUDIT     ETL_RUN_LOG, FILE_LOAD_LOG
                                        REF       COUNTRY (source_code -> iso3 -> table)
```

## Split of responsibilities
| Layer | Python | SQL (Snowflake) |
|---|---|---|
| Ingest | filename/date check, duplicate-file hash, PUT | COPY INTO raw |
| Staging | – | TRY_TO_*, AGE, STALE_MEMBER |
| DQ | – | rules -> DQ_REJECTS |
| Curated | renders per-country DDL/MERGE from REF.COUNTRY | QUALIFY, MERGE |
| Audit | run log, count reconciliation | – |

## Decisions
- RAW is all VARCHAR so a bad value never fails a load; it is rejected later, never dropped.
- Incremental by `file_date`; every step is idempotent (delete-by-file_date + insert, or MERGE).
- Business key is `member_id`. The spec marks Member Name as the key column, which is not unique; flagged in `data_issues_found.md`.
- Country tables are physical (as required) and generated from `REF.COUNTRY`; a new country is a new row, not new code. At scale one table clustered by country plus per-country views is usually better.
- Tables clustered on `(country_code, load_date)`; Snowpipe replaces the COPY step in production.
