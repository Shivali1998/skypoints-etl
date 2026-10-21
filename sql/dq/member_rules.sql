{% from 'sql/macros/common.sql.j2' import q %}
-- Every rule writes (file, row, key, rule, reason). Rows are never dropped silently.
-- How the rules work: every rule is an IFF(<violated?>, <reject details>, NULL) in one list.
-- ARRAY_CONSTRUCT_COMPACT drops the NULLs, LATERAL FLATTEN turns each remaining entry into one
-- DQ_REJECTS row, and the data is read once no matter how many rules there are.
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
SELECT 'MEMBERS', j.file_name, j.row_no, j.mid, v.value:rule::STRING, v.value:reason::STRING, v.value:raw::STRING
FROM (
  -- one pass over j: every rule becomes an object (or NULL), compacted into an array, then flattened
  SELECT *, ARRAY_CONSTRUCT_COMPACT(
      IFF(field_count <> {{ expected_field_count }}, OBJECT_CONSTRUCT('rule', 'FIELD_COUNT_MISMATCH', 'reason', 'expected {{ expected_field_count }} fields', 'raw', field_count::STRING), NULL),
      IFF(raw_name IS NULL, OBJECT_CONSTRUCT('rule', 'MISSING_MANDATORY', 'reason', 'member_name is null', 'raw', NULL), NULL),
      IFF(mid IS NULL, OBJECT_CONSTRUCT('rule', 'MISSING_MANDATORY', 'reason', 'member_id is null', 'raw', NULL), NULL),
      IFF(raw_enroll IS NULL, OBJECT_CONSTRUCT('rule', 'MISSING_MANDATORY', 'reason', 'enrollment_date is null', 'raw', NULL), NULL),
      IFF(mid IS NOT NULL AND NOT REGEXP_LIKE(mid, '{{ member_id_regex }}'), OBJECT_CONSTRUCT('rule', 'BAD_MEMBER_ID_FORMAT', 'reason', 'member_id fails {{ member_id_regex }}', 'raw', mid), NULL),
      IFF(LENGTH(raw_name) > {{ max_len.member_name }}, OBJECT_CONSTRUCT('rule', 'TOO_LONG', 'reason', 'member_name > {{ max_len.member_name }}', 'raw', NULL), NULL),
      IFF(LENGTH(raw_country) > {{ max_len.country }}, OBJECT_CONSTRUCT('rule', 'TOO_LONG', 'reason', 'country > {{ max_len.country }}', 'raw', raw_country), NULL),
      IFF(raw_enroll IS NOT NULL AND enrollment_date IS NULL, OBJECT_CONSTRUCT('rule', 'BAD_ENROLLMENT_DATE', 'reason', 'not a valid {{ date_format }} date', 'raw', raw_enroll), NULL),
      IFF(raw_flight IS NOT NULL AND last_flight_date IS NULL, OBJECT_CONSTRUCT('rule', 'BAD_LAST_FLIGHT_DATE', 'reason', 'not a valid {{ date_format }} date', 'raw', raw_flight), NULL),
      IFF(raw_dob IS NOT NULL AND dob IS NULL, OBJECT_CONSTRUCT('rule', 'BAD_DOB', 'reason', 'not a valid {{ dob_format }} date', 'raw', raw_dob), NULL),
      IFF(age NOT BETWEEN {{ min_age }} AND {{ max_age }}, OBJECT_CONSTRUCT('rule', 'BAD_AGE', 'reason', 'age outside {{ min_age }}..{{ max_age }}', 'raw', age::STRING), NULL),
      IFF(last_flight_date < enrollment_date, OBJECT_CONSTRUCT('rule', 'FLIGHT_BEFORE_ENROLLMENT', 'reason', 'last_flight_date < enrollment_date', 'raw', raw_flight), NULL),
      IFF(dob >= enrollment_date, OBJECT_CONSTRUCT('rule', 'DOB_AFTER_ENROLLMENT', 'reason', 'dob >= enrollment_date', 'raw', raw_dob), NULL),
      IFF(tier_code IS NOT NULL AND tier_code NOT IN ({{ q(tier_codes) }}), OBJECT_CONSTRUCT('rule', 'BAD_TIER', 'reason', 'tier not in {{ tier_codes | join(",") }}', 'raw', raw_tier), NULL),
      IFF(is_active IS NOT NULL AND is_active NOT IN ({{ q(active_flags) }}), OBJECT_CONSTRUCT('rule', 'BAD_ACTIVE_FLAG', 'reason', 'flag not in {{ active_flags | join(",") }}', 'raw', raw_active), NULL),
      IFF(country_iso3 IS NULL, OBJECT_CONSTRUCT('rule', 'UNMAPPED_COUNTRY', 'reason', 'country not in REF.COUNTRY', 'raw', raw_country), NULL),
      IFF(mid IS NOT NULL AND row_no < last_row_for_member, OBJECT_CONSTRUCT('rule', 'DUP_MEMBER_IN_FILE', 'reason', 'superseded by a later row in the same file', 'raw', mid), NULL)
  ) AS violations
  FROM j
) j, LATERAL FLATTEN(input => j.violations) v;
