# AI usage

AI (Claude Code) drafted the DDL, SQL, Python runner, generator and tests from my design. I reviewed the logic that carries risk.

## Where AI output was wrong and got fixed
1. **Field count** – first draft inferred `field_count` from which columns were NULL, which cannot detect a short row. Changed to read the whole line (`FF_LINES`) and count delimiters.
2. **DQ rules** – first draft used `LATERAL (... UNION ALL ... WHERE)` with a window function inside; hard to reason about and untestable. Rewritten as a joined CTE plus plain `UNION ALL` selects.
3. **Jinja** – used a `lambda`, which Jinja doesn't support; replaced with a macro. Caught by rendering every template in `tests/test_render.py`.
4. **Python 3.9** – `str | None` annotations failed on the local interpreter; added `from __future__ import annotations`.
5. **Found only by running on Snowflake** – `REGEXP_COUNT` is not allowed inside a `COPY INTO` transformation, so the field-count approach from item 1 failed at load time. Fixed by landing raw lines in `RAW.RAW_MEMBER_LINES` and parsing with `INSERT..SELECT`. Local DuckDB tests could not have caught this.
6. Design review points kept from the start: member_id (not Member Name) as key, DOB never stored as INT, age corrected for birthdays not yet reached.

## What is and is not verified
- Local (DuckDB/pytest): AGE and STALE_MEMBER macros, the QUALIFY ordering, file checks, that every SQL step renders.
- **Verified on Snowflake (trial account, XSMALL warehouse)**: full pipeline on the spec's sample files; the 2 short member IDs and the `SkyPoints` partner transaction are rejected; members land in the right country tables; a member moving IND -> CAN on a later file leaves TABLE_INDIA and appears only in TABLE_CANADA; a later feed updates a txn status (COMPLETED/CANCELLED) by txn_id; rerunning a file_date is idempotent and an older file does not overwrite newer data.
- **Not verified**: volume. Only a handful of rows have been loaded. The 5M-row generator run and chunked-file COPY timings are still to do.
