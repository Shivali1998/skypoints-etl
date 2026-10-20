-- Latest feed wins per txn_id (PENDING -> COMPLETED). Rejected txns are excluded.
-- Orphans (member not in MEMBER_CURRENT) are kept with member_found = FALSE instead of lost.
MERGE INTO CURATED.FCT_REDEMPTIONS t
USING (
  SELECT s.txn_id, s.member_id, s.feed_date, s.txn_date, s.partner, s.miles_redeemed, s.status,
         (m.member_id IS NOT NULL) AS member_found
  FROM STAGING.STG_REDEMPTIONS s
  LEFT JOIN CURATED.MEMBER_CURRENT m ON m.member_id = s.member_id
  WHERE s.file_date = TO_DATE('{{ file_date }}', 'YYYYMMDD')
    AND NOT EXISTS (SELECT 1 FROM STAGING.DQ_REJECTS d WHERE d.feed = 'REDEMPTIONS' AND d.file_name = s.file_name AND d.business_key = s.txn_id)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY s.txn_id ORDER BY s.feed_date DESC) = 1
) s ON t.txn_id = s.txn_id
WHEN MATCHED AND s.feed_date >= t.feed_date THEN UPDATE SET
  member_id = s.member_id, feed_date = s.feed_date, txn_date = s.txn_date, partner = s.partner,
  miles_redeemed = s.miles_redeemed, status = s.status, member_found = s.member_found
WHEN NOT MATCHED THEN INSERT VALUES
  (s.txn_id, s.member_id, s.feed_date, s.txn_date, s.partner, s.miles_redeemed, s.status, s.member_found);
