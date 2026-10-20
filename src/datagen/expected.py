"""Expected outcomes for generated feeds, computed straight from the files (independent of the SQL under test)."""
from __future__ import annotations

import glob
import json
import re
from collections import Counter
from pathlib import Path

from src.config import load_yaml


def expected_counts(out: Path, file_date: str) -> dict:
    rx = re.compile(load_yaml("member_file_spec.yaml")["member_id_regex"])
    rows, rules, txns, neg = 0, Counter(), 0, 0
    for f in sorted(glob.glob(str(out / f"members_{file_date}*.dat"))):
        for line in open(f):
            if not line.startswith("|D|"):
                continue
            rows += 1
            p = line.rstrip("\n").split("|")[2:]
            # same precedence as datagen: one planted defect per bad row
            if len(p) != 10: rules["FIELD_COUNT_MISMATCH"] += 1
            elif not p[0]: rules["MISSING_MANDATORY"] += 1
            elif not rx.match(p[1]): rules["BAD_MEMBER_ID_FORMAT"] += 1
            elif p[7] == "ZZZ": rules["UNMAPPED_COUNTRY"] += 1
            elif p[4] == "XXX": rules["BAD_TIER"] += 1
            elif p[8] == "99999999": rules["BAD_DOB"] += 1
            elif p[3] < p[2]: rules["FLIGHT_BEFORE_ENROLLMENT"] += 1
    for f in sorted(glob.glob(str(out / f"redemptions_{file_date}*.json"))):
        for line in open(f):
            for t in json.loads(line)["redemptions"]:
                txns += 1
                neg += t["miles_redeemed"] <= 0
    bad = sum(rules.values())
    return {"members": rows, "bad_members": bad, "valid_members": rows - bad, "member_rules": dict(rules),
            "txns": txns, "bad_txns": neg, "valid_txns": txns - neg}
