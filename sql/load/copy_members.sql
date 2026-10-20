-- Detail rows start with '|' so $1 is empty, $2 is the record type.
-- Re-run safe: COPY skips files already loaded (64-day load metadata); the delete covers FORCE reloads.
DELETE FROM RAW.RAW_MEMBERS WHERE file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD');

COPY INTO RAW.RAW_MEMBERS
  (file_name, row_no, file_date, rec_type, member_name, member_id, enrollment_date, last_flight_date,
   tier_code, agent_name, state, country, dob, is_active, field_count)
FROM (
  SELECT METADATA$FILENAME, METADATA$FILE_ROW_NUMBER, TO_DATE('{{ file_date }}', 'YYYYMMDD'),
         $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
         IFF($12 IS NOT NULL, 11, IFF($11 IS NOT NULL, 10, IFF($10 IS NOT NULL, 9, 8)))  -- positions populated incl. rec type; trailing empties undercount, see data_issues
  FROM {{ stage }}/members_{{ file_date }}.dat
)
FILE_FORMAT = (FORMAT_NAME = 'RAW.FF_MEMBERS')
ON_ERROR = CONTINUE;
