from src.datagen.expected import expected_counts
from src.datagen.generate import generate


def test_expected_counts_are_consistent(tmp_path):
    generate(rows=2000, bad_pct=10, file_date="20240119", out=tmp_path, chunks=2)
    e = expected_counts(tmp_path, "20240119")
    assert e["members"] == 2000
    assert e["valid_members"] == 2000 - e["bad_members"] > 0
    assert e["bad_members"] == sum(e["member_rules"].values())
    assert e["valid_txns"] == e["txns"] - e["bad_txns"]
    assert e["bad_txns"] == e["bad_members"]    # generator plants one negative-miles txn per bad row
