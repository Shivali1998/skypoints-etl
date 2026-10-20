DELETE FROM RAW.RAW_REDEMPTIONS WHERE file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD');

COPY INTO RAW.RAW_REDEMPTIONS (file_name, row_no, file_date, v)
FROM (SELECT METADATA$FILENAME, METADATA$FILE_ROW_NUMBER, TO_DATE('{{ file_date }}', 'YYYYMMDD'), $1
      FROM {{ stage }}/redemptions_{{ file_date }}.json)
FILE_FORMAT = (FORMAT_NAME = 'RAW.FF_JSON')
ON_ERROR = CONTINUE;
