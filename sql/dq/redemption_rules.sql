{% from 'sql/macros/common.sql.j2' import q %}
-- Same one-pass pattern as member_rules.sql: IFF per rule -> array of violations -> FLATTEN.
DELETE FROM STAGING.DQ_REJECTS WHERE feed = 'REDEMPTIONS' AND file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD');

INSERT INTO STAGING.DQ_REJECTS (feed, file_date, file_name, row_no, business_key, rule_code, reason, raw_value)
WITH j AS (SELECT * FROM STAGING.STG_REDEMPTIONS WHERE file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD'))
SELECT 'REDEMPTIONS', j.file_date, j.file_name, NULL, j.txn_id, v.value:rule::STRING, v.value:reason::STRING, v.value:raw::STRING
FROM (
  SELECT *, ARRAY_CONSTRUCT_COMPACT(
      IFF(txn_id IS NULL OR member_id IS NULL, OBJECT_CONSTRUCT('rule', 'MISSING_MANDATORY', 'reason', 'txn_id or member_id null', 'raw', NULL), NULL),
      IFF(miles_redeemed IS NULL OR miles_redeemed <= 0, OBJECT_CONSTRUCT('rule', 'BAD_MILES', 'reason', 'miles_redeemed must be > 0', 'raw', miles_redeemed::STRING), NULL),
      IFF(status IS NULL OR status NOT IN ({{ q(statuses) }}), OBJECT_CONSTRUCT('rule', 'BAD_STATUS', 'reason', 'status not in {{ statuses | join(",") }}', 'raw', status), NULL),
      IFF(partner IS NULL OR partner NOT IN ({{ q(partners) }}), OBJECT_CONSTRUCT('rule', 'BAD_PARTNER', 'reason', 'partner not in whitelist', 'raw', partner), NULL),
      IFF(txn_date IS NULL OR txn_date > feed_date, OBJECT_CONSTRUCT('rule', 'BAD_TXN_DATE', 'reason', 'txn_date null or after feed_date', 'raw', txn_date::STRING), NULL)
  ) AS violations
  FROM j
) j, LATERAL FLATTEN(input => j.violations) v;
