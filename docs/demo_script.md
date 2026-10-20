# Demo script
1. `python -m src.datagen.generate --rows 5000000 --bad-pct 2` → upload to `@SKYPOINTS_STAGE` (split into ~100–250 MB chunks).
2. `python -m src.pipeline.runner --date 20240115` → show `AUDIT.ETL_RUN_LOG` counts per step.
3. `SELECT rule_code, COUNT(*) FROM STAGING.DQ_REJECTS GROUP BY 1;` → bad rows are explained, not dropped.
4. Move a member between countries in a second file (`--date 20240116`); show them only in the new `TABLE_*`.
5. `SELECT * FROM CURATED.V_MEMBER_REDEMPTIONS LIMIT 20;` and an orphan check: `WHERE member_found = FALSE` on `FCT_REDEMPTIONS`.
