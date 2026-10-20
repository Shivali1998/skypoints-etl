# AI usage

AI (Claude Code) drafted the DDL, SQL, Python runner, generator and tests from my design. I reviewed the logic that carries risk.

## Where AI output was wrong and got fixed
1. **Field count** – first draft inferred `field_count` from which columns were NULL, which cannot detect a short row. Changed to read the whole line (`FF_LINES`) and count delimiters.
2. **DQ rules** – first draft used `LATERAL (... UNION ALL ... WHERE)` with a window function inside; hard to reason about and untestable. Rewritten as a joined CTE plus plain `UNION ALL` selects.
3. **Jinja** – used a `lambda`, which Jinja doesn't support; replaced with a macro. Caught by rendering every template in `tests/test_render.py`.
4. **Python 3.9** – `str | None` annotations failed on the local interpreter; added `from __future__ import annotations`.
5. Design review points kept from the start: member_id (not Member Name) as key, DOB never stored as INT, age corrected for birthdays not yet reached.

## What is and is not verified
- Verified locally (DuckDB/pytest): AGE and STALE_MEMBER macros, the QUALIFY ordering, file-name/header checks, that every SQL step renders.
- **Not verified**: the Snowflake-specific SQL (COPY INTO, MERGE, LATERAL FLATTEN, TRY_TO_DATE) has not been run against a Snowflake account. Run `python -m src.pipeline.runner --date 20240115` on a trial account before the demo.
