{% macro q(xs) %}{% for x in xs %}'{{ x }}'{{ ',' if not loop.last }}{% endfor %}{% endmacro %}
-- Every rule writes (file,row,key,rule,reason). Rows are never dropped silently.
DELETE FROM STAGING.DQ_REJECTS
WHERE feed = 'MEMBERS'
  AND file_name IN (SELECT DISTINCT file_name FROM RAW.RAW_MEMBERS WHERE file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD'));

INSERT INTO STAGING.DQ_REJECTS (feed, file_name, row_no, business_key, rule_code, reason, raw_value)
WITH j AS (
  SELECT r.file_name, r.row_no, r.member_id AS mid, r.member_name AS raw_name, r.field_count,
         r.enrollment_date AS raw_enroll, r.last_flight_date AS raw_flight, r.dob AS raw_dob,
         r.tier_code AS raw_tier, r.is_active AS raw_active, r.country AS raw_country,
         s.enrollment_date, s.last_flight_date, s.dob, s.tier_code, s.is_active, s.country_iso3, s.age,
         MAX(r.row_no) OVER (PARTITION BY r.file_name, r.member_id) AS last_row_for_member
  FROM RAW.RAW_MEMBERS r
  JOIN STAGING.STG_MEMBERS s ON s.file_name = r.file_name AND s.row_no = r.row_no
  WHERE r.file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD') AND r.rec_type = 'D'
)
SELECT 'MEMBERS', file_name, row_no, mid, rule_code, reason, raw_value FROM (
            SELECT *, 'FIELD_COUNT_MISMATCH' rule_code, 'expected {{ expected_field_count }} fields' reason, field_count::STRING raw_value FROM j WHERE field_count <> {{ expected_field_count }}
  UNION ALL SELECT *, 'MISSING_MANDATORY', 'member_name is null', NULL FROM j WHERE raw_name IS NULL
  UNION ALL SELECT *, 'MISSING_MANDATORY', 'member_id is null', NULL FROM j WHERE mid IS NULL
  UNION ALL SELECT *, 'MISSING_MANDATORY', 'enrollment_date is null', NULL FROM j WHERE raw_enroll IS NULL
  UNION ALL SELECT *, 'BAD_MEMBER_ID_FORMAT', 'member_id fails {{ member_id_regex }}', mid FROM j WHERE mid IS NOT NULL AND NOT REGEXP_LIKE(mid, '{{ member_id_regex }}')
  UNION ALL SELECT *, 'TOO_LONG', 'member_name > {{ max_len.member_name }}', NULL FROM j WHERE LENGTH(raw_name) > {{ max_len.member_name }}
  UNION ALL SELECT *, 'TOO_LONG', 'country > {{ max_len.country }}', raw_country FROM j WHERE LENGTH(raw_country) > {{ max_len.country }}
  UNION ALL SELECT *, 'BAD_ENROLLMENT_DATE', 'not a valid {{ date_format }} date', raw_enroll FROM j WHERE raw_enroll IS NOT NULL AND enrollment_date IS NULL
  UNION ALL SELECT *, 'BAD_LAST_FLIGHT_DATE', 'not a valid {{ date_format }} date', raw_flight FROM j WHERE raw_flight IS NOT NULL AND last_flight_date IS NULL
  UNION ALL SELECT *, 'BAD_DOB', 'not a valid {{ dob_format }} date', raw_dob FROM j WHERE raw_dob IS NOT NULL AND dob IS NULL
  UNION ALL SELECT *, 'BAD_AGE', 'age outside {{ min_age }}..{{ max_age }}', age::STRING FROM j WHERE age NOT BETWEEN {{ min_age }} AND {{ max_age }}
  UNION ALL SELECT *, 'FLIGHT_BEFORE_ENROLLMENT', 'last_flight_date < enrollment_date', raw_flight FROM j WHERE last_flight_date < enrollment_date
  UNION ALL SELECT *, 'DOB_AFTER_ENROLLMENT', 'dob >= enrollment_date', raw_dob FROM j WHERE dob >= enrollment_date
  UNION ALL SELECT *, 'BAD_TIER', 'tier not in {{ tier_codes | join(",") }}', raw_tier FROM j WHERE tier_code IS NOT NULL AND tier_code NOT IN ({{ q(tier_codes) }})
  UNION ALL SELECT *, 'BAD_ACTIVE_FLAG', 'flag not in {{ active_flags | join(",") }}', raw_active FROM j WHERE is_active IS NOT NULL AND is_active NOT IN ({{ q(active_flags) }})
  UNION ALL SELECT *, 'UNMAPPED_COUNTRY', 'country not in REF.COUNTRY', raw_country FROM j WHERE country_iso3 IS NULL
  -- Key uniqueness: a member repeated inside one file keeps only its last row.
  UNION ALL SELECT *, 'DUP_MEMBER_IN_FILE', 'superseded by a later row in the same file', mid FROM j WHERE mid IS NOT NULL AND row_no < last_row_for_member
);
