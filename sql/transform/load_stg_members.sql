{% from 'sql/macros/derived.sql.j2' import age, stale %}
-- Idempotent: replace this file_date's slice. Typing failures become NULL and are caught by DQ rules.
DELETE FROM STAGING.STG_MEMBERS WHERE file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD');

INSERT INTO STAGING.STG_MEMBERS
  (file_name, row_no, file_date, member_name, member_id, enrollment_date, last_flight_date,
   tier_code, agent_name, state, country_src, country_iso3, dob, is_active, age, stale_member)
WITH typed AS (
  SELECT r.file_name, r.row_no, r.file_date, r.member_name, r.member_id,
         TRY_TO_DATE(r.enrollment_date, '{{ date_format }}') AS enrollment_date,
         TRY_TO_DATE(r.last_flight_date, '{{ date_format }}') AS last_flight_date,
         UPPER(r.tier_code) AS tier_code, r.agent_name, r.state, r.country AS country_src,
         c.iso3 AS country_iso3,
         TRY_TO_DATE(r.dob, '{{ dob_format }}') AS dob, UPPER(r.is_active) AS is_active
  FROM RAW.RAW_MEMBERS r
  LEFT JOIN REF.COUNTRY c ON UPPER(r.country) = c.source_code
  WHERE r.file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD') AND r.rec_type = 'D'
)
SELECT *,
       {{ age('dob', 'CURRENT_DATE') }},
       {{ stale('last_flight_date', 'CURRENT_DATE', stale_days) }}
FROM typed;
