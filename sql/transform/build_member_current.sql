-- Latest record wins: newest file, then newest flight, then last row in the file.
-- Rows rejected by DQ are excluded with an anti-join (no UPDATE on billions of rows).
CREATE OR REPLACE TRANSIENT TABLE STAGING.MEMBER_LATEST AS
SELECT s.* FROM STAGING.STG_MEMBERS s
WHERE s.file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD')
  AND NOT EXISTS (SELECT 1 FROM STAGING.DQ_REJECTS d
                  WHERE d.feed = 'MEMBERS' AND d.file_name = s.file_name AND d.row_no = s.row_no)
QUALIFY ROW_NUMBER() OVER (PARTITION BY s.member_id
        ORDER BY s.file_date DESC, s.last_flight_date DESC NULLS LAST, s.file_name DESC, s.row_no DESC) = 1;

MERGE INTO CURATED.MEMBER_CURRENT t USING STAGING.MEMBER_LATEST s ON t.member_id = s.member_id
WHEN MATCHED AND s.file_date >= t.source_file_date THEN UPDATE SET
  member_name = s.member_name, enrollment_date = s.enrollment_date, last_flight_date = s.last_flight_date,
  tier_code = s.tier_code, agent_name = s.agent_name, state = s.state, country_iso3 = s.country_iso3,
  dob = s.dob, is_active = s.is_active, age = s.age, stale_member = s.stale_member,
  source_file_date = s.file_date, updated_ts = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT
  (member_id, member_name, enrollment_date, last_flight_date, tier_code, agent_name, state,
   country_iso3, dob, is_active, age, stale_member, source_file_date)
VALUES (s.member_id, s.member_name, s.enrollment_date, s.last_flight_date, s.tier_code, s.agent_name,
        s.state, s.country_iso3, s.dob, s.is_active, s.age, s.stale_member, s.file_date);
