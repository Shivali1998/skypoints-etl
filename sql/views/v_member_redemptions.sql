-- Join key: member_id (LEFT JOIN so members without redemptions stay visible).
CREATE OR REPLACE VIEW CURATED.V_MEMBER_REDEMPTIONS AS
SELECT m.member_id, m.member_name, m.country_iso3, m.tier_code, m.stale_member,
       r.txn_id, r.txn_date, r.partner, r.miles_redeemed, r.status
FROM CURATED.MEMBER_CURRENT m
LEFT JOIN CURATED.FCT_REDEMPTIONS r ON r.member_id = m.member_id;
