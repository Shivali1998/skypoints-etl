{% macro q(xs) %}{% for x in xs %}'{{ x }}'{{ ',' if not loop.last }}{% endfor %}{% endmacro %}
DELETE FROM STAGING.DQ_REJECTS WHERE feed = 'REDEMPTIONS'
  AND file_name IN (SELECT DISTINCT file_name FROM STAGING.STG_REDEMPTIONS WHERE file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD'));

INSERT INTO STAGING.DQ_REJECTS (feed, file_name, row_no, business_key, rule_code, reason, raw_value)
WITH j AS (SELECT * FROM STAGING.STG_REDEMPTIONS WHERE file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD'))
SELECT 'REDEMPTIONS', file_name, NULL, txn_id, rule_code, reason, raw_value FROM (
            SELECT *, 'MISSING_MANDATORY' rule_code, 'txn_id or member_id null' reason, NULL raw_value FROM j WHERE txn_id IS NULL OR member_id IS NULL
  UNION ALL SELECT *, 'BAD_MILES', 'miles_redeemed must be > 0', miles_redeemed::STRING FROM j WHERE miles_redeemed IS NULL OR miles_redeemed <= 0
  UNION ALL SELECT *, 'BAD_STATUS', 'status not in {{ statuses | join(",") }}', status FROM j WHERE status IS NULL OR status NOT IN ({{ q(statuses) }})
  UNION ALL SELECT *, 'BAD_PARTNER', 'partner not in whitelist', partner FROM j WHERE partner IS NULL OR partner NOT IN ({{ q(partners) }})
  UNION ALL SELECT *, 'BAD_TXN_DATE', 'txn_date null or after feed_date', txn_date::STRING FROM j WHERE txn_date IS NULL OR txn_date > feed_date
);
