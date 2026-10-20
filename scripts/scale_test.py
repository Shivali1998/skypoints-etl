"""Generate N members (+ redemptions), run the pipeline on Snowflake, and check every count against the files.

  python scripts/scale_test.py --rows 1000000 --chunks 4 --date 20240118 --id-start 2000000
Use a fresh --date and --id-start per run. Needs SNOWFLAKE_* env vars (see README). Exit code 1 if any check fails.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.datagen.expected import expected_counts  # noqa: E402
from src.datagen.generate import generate  # noqa: E402
from src.db.snowflake_client import SnowflakeClient  # noqa: E402
from src.pipeline.runner import run  # noqa: E402

COUNTRY_TABLES = ["TABLE_USA", "TABLE_INDIA", "TABLE_PHILIPPINES", "TABLE_CANADA", "TABLE_AUSTRALIA"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=1_000_000)
    ap.add_argument("--chunks", type=int, default=4)
    ap.add_argument("--bad-pct", type=float, default=2.0)
    ap.add_argument("--date", default="20240118")
    ap.add_argument("--id-start", type=int, default=2_000_000)
    a = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        generate(a.rows, a.bad_pct, a.date, out, chunks=a.chunks, id_start=a.id_start)
        exp = expected_counts(out, a.date)
        t0 = time.time()
        run(a.date, data_dir=str(out))
        print(f"pipeline wall time incl. upload: {time.time() - t0:.0f}s")

    c = SnowflakeClient()
    d = f"TO_DATE('{a.date}','YYYYMMDD')"
    q = c.scalar
    got_rules = dict(c.conn.cursor().execute(
        f"SELECT rule_code, COUNT(*) FROM STAGING.DQ_REJECTS WHERE feed='MEMBERS' AND file_name LIKE '%{a.date}%' GROUP BY 1").fetchall())
    union = " UNION ALL ".join(f"SELECT member_id FROM CURATED.{t}" for t in COUNTRY_TABLES)
    checks = [
        ("raw member rows", q(f"SELECT COUNT(*) FROM RAW.RAW_MEMBERS WHERE rec_type='D' AND file_date={d}"), exp["members"]),
        ("staged member rows", q(f"SELECT COUNT(*) FROM STAGING.STG_MEMBERS WHERE file_date={d}"), exp["members"]),
        ("valid members in MEMBER_CURRENT", q(f"SELECT COUNT(*) FROM CURATED.MEMBER_CURRENT WHERE source_file_date={d}"), exp["valid_members"]),
        ("transactions staged", q(f"SELECT COUNT(*) FROM STAGING.STG_REDEMPTIONS WHERE file_date={d}"), exp["txns"]),
        ("transactions loaded", q(f"SELECT COUNT(*) FROM CURATED.FCT_REDEMPTIONS WHERE feed_date={d}"), exp["valid_txns"]),
        ("BAD_MILES rejects", q(f"SELECT COUNT(*) FROM STAGING.DQ_REJECTS WHERE rule_code='BAD_MILES' AND file_name LIKE '%{a.date}%'"), exp["bad_txns"]),
        ("country tables: rows == distinct members", q(f"SELECT COUNT(*) - COUNT(DISTINCT member_id) FROM ({union})"), 0),
    ] + [(f"rejects {r}", got_rules.get(r, 0), n) for r, n in sorted(exp["member_rules"].items())]

    failed = 0
    for name, got, want in checks:
        ok = got == want
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name:<42} got={got:<9} expected={want}")
    extra = {r: n for r, n in got_rules.items() if r not in exp["member_rules"]}
    if extra:
        print(f"note: additional member rejects not planted by the generator: {extra}")
    print("ALL CHECKS PASSED" if not failed else f"{failed} CHECK(S) FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
