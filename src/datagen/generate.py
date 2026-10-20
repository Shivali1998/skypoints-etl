"""Synthetic feeds for the demo: python -m src.datagen.generate --rows 5000000 --bad-pct 2 --date 20240115"""
from __future__ import annotations

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

COUNTRIES = ["USA", "IND", "PHIL", "CAN", "AU", "US", "IN"]
STATES = {"USA": "CA", "US": "CA", "IND": "TN", "IN": "KA", "PHIL": "NCR", "CAN": "ONT", "AU": "VIC"}
TIERS = ["GLD", "SLV", "PLT"]
PARTNERS = ["AeroLink", "SkyBridge", "GlobeAir"]
HEADER = "|H|Member_Name|Member_Id|Enrollment_Date|Last_Flight_Date|Tier_Code|Agent_Name|State|Country|DOB|Is_Active"


def _d(d: date) -> str:
    return d.strftime("%Y%m%d")


def member_line(rng: random.Random, i: int, bad: bool) -> str:
    enroll = date(2005, 1, 1) + timedelta(days=rng.randint(0, 5000))
    flight = enroll + timedelta(days=rng.randint(0, 4000))
    dob = date(1940, 1, 1) + timedelta(days=rng.randint(0, 22000))
    country = rng.choice(COUNTRIES)
    f = [f"Member{i}", str(100000 + i), _d(enroll), _d(flight), rng.choice(TIERS), "Sam",
         STATES[country], country, dob.strftime("%d%m%Y"), rng.choice("AI")]
    if bad:  # one deliberate defect per bad row
        kind = rng.choice(["id", "dob", "country", "tier", "name", "fields", "flight"])
        if kind == "id": f[1] = str(rng.randint(1, 9999))
        elif kind == "dob": f[8] = "99999999"
        elif kind == "country": f[7] = "ZZZ"
        elif kind == "tier": f[4] = "XXX"
        elif kind == "name": f[0] = ""
        elif kind == "fields": f.pop()
        else: f[3] = _d(enroll - timedelta(days=30))
    return "|D|" + "|".join(f)


def redemption_doc(rng: random.Random, i: int, feed_date: str, bad: bool) -> dict:
    txns = []
    for k in range(rng.randint(1, 3)):
        txns.append({"txn_id": f"RX{i}_{k}", "txn_date": feed_date, "partner": rng.choice(PARTNERS),
                     "miles_redeemed": -5 if bad and k == 0 else rng.randint(500, 50000),
                     "status": rng.choice(["COMPLETED", "PENDING"])})
    return {"member_id": str(100000 + i), "feed_date": feed_date, "redemptions": txns}


def generate(rows: int, bad_pct: float, file_date: str, out: Path, seed: int = 42,
             chunks: int = 1, id_start: int = 0) -> None:
    """Write `chunks` member files + `chunks` NDJSON files (members_<date>_001.dat ...) so COPY loads them in parallel."""
    rng = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)
    per = -(-rows // chunks)
    for c in range(chunks):
        suffix = f"_{c + 1:03d}" if chunks > 1 else ""
        lo, hi = c * per, min(rows, (c + 1) * per)
        with open(out / f"members_{file_date}{suffix}.dat", "w") as m, \
             open(out / f"redemptions_{file_date}{suffix}.json", "w") as r:
            m.write(HEADER + "\n")
            for i in range(lo, hi):
                bad = rng.random() * 100 < bad_pct
                m.write(member_line(rng, id_start + i, bad) + "\n")
                r.write(json.dumps(redemption_doc(rng, id_start + i, file_date, bad)) + "\n")  # NDJSON, splittable


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=100_000)
    ap.add_argument("--bad-pct", type=float, default=2.0)
    ap.add_argument("--date", default="20240115")
    ap.add_argument("--out", default="data/generated")
    ap.add_argument("--chunks", type=int, default=1, help="split into N files (~100-250 MB each at scale)")
    ap.add_argument("--id-start", type=int, default=0, help="first member id offset (avoid colliding with earlier days)")
    a = ap.parse_args()
    generate(a.rows, a.bad_pct, a.date, Path(a.out), chunks=a.chunks, id_start=a.id_start)
