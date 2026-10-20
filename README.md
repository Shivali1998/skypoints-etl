# SkyPoints ETL

Daily load of an airline loyalty programme's members into per-country tables on Snowflake, plus a
semi-structured redemption feed. SQL-first ELT: SQL does all data work, so billions of rows never leave the
warehouse; Python orchestrates, renders per-country SQL from config, generates test data and runs tests.

## The two input feeds

### 1. Member flat file: `members_<YYYYMMDD>[_NNN].dat` (pipe-delimited)
One header record (`|H|`) and one detail record (`|D|`) per member. Large days are split into `_NNN` chunks that load in parallel.
```
|H|Member_Name|Member_Id|Enrollment_Date|Last_Flight_Date|Tier_Code|Agent_Name|State|Country|DOB|Is_Active
|D|Elena|223457|20101012|20121013|GLD|Sam|CA|USA|03051985|A
|D|Ravi|223458|20101012|20121013|SLV|Sam|TN|IND|03051985|A
```
| Pos | Column | Length | Type | Mandatory | Notes |
|---|---|---|---|---|---|
| 1 | Member Name | 255 | VARCHAR | Y | spec marks it as the key column; we key on Member ID (see below) |
| 2 | Member ID | 18 | VARCHAR | Y | business key |
| 3 | Enrollment Date | 8 | DATE | Y | YYYYMMDD |
| 4 | Last Flight Date | 8 | DATE | N | YYYYMMDD; drives `Stale_Member` (> 90 days) |
| 5 | Tier Code | 5 | CHAR | N | GLD / SLV / PLT |
| 6 | Agent Name | 255 | CHAR | N | |
| 7 | State | 5 | CHAR | N | |
| 8 | Country | 5 | CHAR | N | mixed ISO-3 / ISO-2 / ad hoc; mapped via `REF.COUNTRY` |
| 9 | Post Code | 5 | INT | N | in the spec table but absent from the header/detail records, so not loaded |
| 10 | Date of Birth | 8 | DATE | N | sample is `03051985` (DDMMYYYY), unlike the other dates; drives `Age` |
| 11 | Active Member | 1 | CHAR | N | A / I |

### 2. Redemption feed: `redemptions_<YYYYMMDD>[_NNN].json` (one JSON document per member)
```json
{ "member_id": "223457", "feed_date": "20240115",
  "redemptions": [
    { "txn_id": "RX10091", "txn_date": "20240110", "partner": "AeroLink", "miles_redeemed": 12000, "status": "COMPLETED" },
    { "txn_id": "RX10092", "txn_date": "20240113", "partner": "SkyPoints", "miles_redeemed": 5000,  "status": "PENDING" } ] }
```
Flattened with `LATERAL FLATTEN` to one row per transaction; the latest feed wins per `txn_id` (PENDING -> COMPLETED);
joined to members on `member_id` (`CURATED.V_MEMBER_REDEMPTIONS`). Transactions for unknown members are kept with `member_found = FALSE`.

### What happens to them
```
flat file / JSON -> @stage -> RAW (all VARCHAR/VARIANT) -> STAGING (typed, AGE, STALE_MEMBER, DQ_REJECTS)
                 -> CURATED (MEMBER_CURRENT -> TABLE_INDIA / TABLE_USA / ..., FCT_REDEMPTIONS)
```
Details and decisions: `docs/architecture.md`. Issues found in the sample data and how each is handled: `docs/data_issues_found.md`.

## Run
```
pip install -r requirements.txt
pytest                                                    # 26 local tests (DuckDB, no Snowflake needed)
python -m src.pipeline.runner --date 20240115 --dry-run   # print the rendered SQL, no connection
```
Against Snowflake (creates the `SKYPOINTS` database, schemas, stage, tables and an XSMALL warehouse on first run):
```
export SNOWFLAKE_ACCOUNT=<org-account> SNOWFLAKE_USER=<login name>
export SNOWFLAKE_PASSWORD=...            # or, if the account is SSO-only / MFA:
export SNOWFLAKE_TOKEN=...               # programmatic access token
python -m src.pipeline.runner --date 20240115 [--data-dir data/sample]
```
- Token (PAT) logins require a network policy on the user, e.g.
  `CREATE NETWORK POLICY p ALLOWED_IP_LIST=('<your ip>'); ALTER USER "<user>" SET NETWORK_POLICY=p;`
- The connector wants the **login name** (often the email); `ALTER USER` wants the **user name** (case-sensitive when quoted).

## Tests
- **Unit (local, DuckDB):** age/stale edge cases, latest-record-wins, file-name/header checks, SQL rendering, generator. `pytest`.
- **Scale test (Snowflake):** `python scripts/scale_test.py --rows 1000000 --chunks 4 --date 20240118 --id-start 2000000`
  generates 1M members (~2M transactions, 2% planted defects), runs the pipeline and asserts every count against the files.
  Measured on an XSMALL trial warehouse: all 9 pipeline steps ~33 s, every check passed. Full results and limits: `docs/scale_test.md`.
  This is millions, not billions; see the limits section there.

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
