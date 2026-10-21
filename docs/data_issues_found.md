# Data issues found in the spec/sample

| # | Issue | Handling |
|---|---|---|
| 1 | Member Name is the key column in the spec | Use `member_id` as business key; rule `DUP_MEMBER_IN_FILE` |
| 2 | Spec lists 11 fields (Post Code); header/detail have 10 | Layout follows header; `FIELD_COUNT_MISMATCH` rule |
| 3 | DOB `03051985` differs from other dates (YYYYMMDD) | Explicit `dob_format` in config, `TRY_TO_DATE`, `BAD_DOB` |
| 4 | Staging shows DOB `3051985` (leading zero lost: stored as INT) | RAW/STG keep strings until cast |
| 5 | Staging column `County` and Agent_Name blank for Ravi.. | Column mapping reconciled in tests; blank agent allowed (not mandatory) |
| 6 | Country codes mix ISO-3, ISO-2, ad hoc (USA, IND, PHIL, CAN, AU) | `REF.COUNTRY` mapping; `UNMAPPED_COUNTRY` |
| 7 | Member IDs 22345 / 2256 shorter than others | `member_id_regex` rule `BAD_MEMBER_ID_FORMAT` (assumption: 6–18 digits; confirm) |
| 8 | All last flights in 2012 → every member stale | Reported, not rejected; sanity rules on date order |
| 9 | JSON partner `SkyPoints` is the program itself; PENDING txns | partner whitelist; latest feed wins per `txn_id` |

## Assumptions (confirm with the source owner)
- **DOB format** is DDMMYYYY (`03051985` = 3 May 1985); set in `config/member_file_spec.yaml` (`dob_format`).
- **Member ID** is 6-18 digits, so the sample's `22345` and `2256` are rejected (`member_id_regex`).
- **Business key** is `member_id`; Member Name (marked key in the spec) is not unique.
- **Layout** follows the header record (10 fields); Post Code is in the spec table but not in the records, so it is not loaded.
- **Partner whitelist, tier codes and status values** are in `config/`; `SkyPoints` is rejected as a partner because it is the programme itself.
- **Country tables** are physical, as the brief asks; at scale one clustered table with per-country views is usually better.
