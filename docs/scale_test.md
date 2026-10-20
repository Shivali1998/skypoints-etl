# Scale test: 1,000,000 members (measured, Snowflake trial, XSMALL warehouse)

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


## Reproduce
```
python scripts/scale_test.py --rows 1000000 --chunks 4 --date 20240118 --id-start 2000000
```
Generates the feeds, runs the pipeline on Snowflake, and compares every count with what is in the files
(exits non-zero on any mismatch). Use a fresh `--date` and `--id-start` for each run. A 20,000-row run takes ~40 s.
