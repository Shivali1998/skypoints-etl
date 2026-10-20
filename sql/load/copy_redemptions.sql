DELETE FROM RAW.RAW_REDEMPTIONS WHERE file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD');

COPY INTO RAW.RAW_REDEMPTIONS (file_name, row_no, file_date, v)
FROM (SELECT METADATA$FILENAME, METADATA$FILE_ROW_NUMBER, TO_DATE('{{ file_date }}', 'YYYYMMDD'), $1
      FROM {{ stage }}/)
PATTERN = '.*redemptions_{{ file_date }}(_[0-9]+)?[.]json([.]gz)?'
FILE_FORMAT = (FORMAT_NAME = 'RAW.FF_JSON')
FORCE = TRUE   -- the delete above makes a reload idempotent; don't let load metadata skip the file
ON_ERROR = CONTINUE;
