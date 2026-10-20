-- Detail rows look like |D|Elena|223457|...; part 1 is empty, part 2 is the record type.
-- Delete-then-load makes a FORCE rerun of the same file_date idempotent.
DELETE FROM RAW.RAW_MEMBERS WHERE file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD');

COPY INTO RAW.RAW_MEMBERS
  (file_name, row_no, file_date, rec_type, member_name, member_id, enrollment_date, last_flight_date,
   tier_code, agent_name, state, country, dob, is_active, field_count)
FROM (
  SELECT METADATA$FILENAME, METADATA$FILE_ROW_NUMBER, TO_DATE('{{ file_date }}', 'YYYYMMDD'),
         NULLIF(TRIM(SPLIT_PART($1, '|', 2)), ''),  NULLIF(TRIM(SPLIT_PART($1, '|', 3)), ''),
         NULLIF(TRIM(SPLIT_PART($1, '|', 4)), ''),  NULLIF(TRIM(SPLIT_PART($1, '|', 5)), ''),
         NULLIF(TRIM(SPLIT_PART($1, '|', 6)), ''),  NULLIF(TRIM(SPLIT_PART($1, '|', 7)), ''),
         NULLIF(TRIM(SPLIT_PART($1, '|', 8)), ''),  NULLIF(TRIM(SPLIT_PART($1, '|', 9)), ''),
         NULLIF(TRIM(SPLIT_PART($1, '|', 10)), ''), NULLIF(TRIM(SPLIT_PART($1, '|', 11)), ''),
         NULLIF(TRIM(SPLIT_PART($1, '|', 12)), ''),
         REGEXP_COUNT($1, '[|]') - 1   -- delimiters minus the leading one = data fields incl. record type
  FROM {{ stage }}/members_{{ file_date }}.dat
)
FILE_FORMAT = (FORMAT_NAME = 'RAW.FF_LINES')
ON_ERROR = CONTINUE;
