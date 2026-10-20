DELETE FROM STAGING.STG_REDEMPTIONS WHERE file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD');

INSERT INTO STAGING.STG_REDEMPTIONS
  (file_name, file_date, member_id, feed_date, txn_id, txn_date, partner, miles_redeemed, status)
SELECT r.file_name, r.file_date,
       r.v:member_id::STRING,
       TRY_TO_DATE(r.v:feed_date::STRING, '{{ date_format }}'),
       f.value:txn_id::STRING,
       TRY_TO_DATE(f.value:txn_date::STRING, '{{ date_format }}'),
       f.value:partner::STRING,
       TRY_TO_NUMBER(f.value:miles_redeemed::STRING),
       UPPER(f.value:status::STRING)
FROM RAW.RAW_REDEMPTIONS r, LATERAL FLATTEN(input => r.v:redemptions) f
WHERE r.file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD');
