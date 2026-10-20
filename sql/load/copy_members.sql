-- Detail rows look like |D|Elena|223457|...; part 1 is empty, part 2 is the record type.
-- Delete-then-load makes a FORCE rerun of the same file_date idempotent.
DELETE FROM RAW.RAW_MEMBER_LINES WHERE file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD');
DELETE FROM RAW.RAW_MEMBERS WHERE file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD');

COPY INTO RAW.RAW_MEMBER_LINES (file_name, row_no, file_date, line)
FROM (SELECT METADATA$FILENAME, METADATA$FILE_ROW_NUMBER, TO_DATE('{{ file_date }}', 'YYYYMMDD'), $1
      FROM {{ stage }}/)
PATTERN = '.*members_{{ file_date }}(_[0-9]+)?[.]dat([.]gz)?'   -- all chunks of the day load in parallel
FILE_FORMAT = (FORMAT_NAME = 'RAW.FF_LINES')
FORCE = TRUE
ON_ERROR = CONTINUE;

INSERT INTO RAW.RAW_MEMBERS
  (file_name, row_no, file_date, rec_type, member_name, member_id, enrollment_date, last_flight_date,
   tier_code, agent_name, state, country, dob, is_active, field_count)
SELECT file_name, row_no, file_date,
       NULLIF(TRIM(SPLIT_PART(line, '|', 2)), ''),  NULLIF(TRIM(SPLIT_PART(line, '|', 3)), ''),
       NULLIF(TRIM(SPLIT_PART(line, '|', 4)), ''),  NULLIF(TRIM(SPLIT_PART(line, '|', 5)), ''),
       NULLIF(TRIM(SPLIT_PART(line, '|', 6)), ''),  NULLIF(TRIM(SPLIT_PART(line, '|', 7)), ''),
       NULLIF(TRIM(SPLIT_PART(line, '|', 8)), ''),  NULLIF(TRIM(SPLIT_PART(line, '|', 9)), ''),
       NULLIF(TRIM(SPLIT_PART(line, '|', 10)), ''), NULLIF(TRIM(SPLIT_PART(line, '|', 11)), ''),
       NULLIF(TRIM(SPLIT_PART(line, '|', 12)), ''),
       REGEXP_COUNT(line, '[|]') - 1   -- delimiters minus the leading one = data fields (record type not counted)
FROM RAW.RAW_MEMBER_LINES
WHERE file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD');
