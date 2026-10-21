from src.config import load_yaml
from src.ingest.file_checks import check_member_header, check_name

SPEC = load_yaml("member_file_spec.yaml")


def test_valid_name():
    r = check_name("members_20240115.dat", SPEC["file_name_pattern"])
    assert r.ok and r.file_date == "20240115"


def test_bad_names():
    assert not check_name("members_20241315.dat", SPEC["file_name_pattern"]).ok   # month 13
    assert not check_name("members_20240115.csv", SPEC["file_name_pattern"]).ok
    assert not check_name("member_20240115.dat", SPEC["file_name_pattern"]).ok


def test_header_matches_layout():
    line = "|H|Member_Name|Member_Id|Enrollment_Date|Last_Flight_Date|Tier_Code|Agent_Name|State|Country|DOB|Is_Active"
    assert check_member_header(line, SPEC["columns"])
    assert not check_member_header(line.replace("Country", "County"), SPEC["columns"])


def test_validate_files_accepts_good_and_rejects_bad(tmp_path):
    import pytest
    from src.ingest.file_checks import validate_files
    red = load_yaml("redemption_spec.yaml")
    hdr = "|H|Member_Name|Member_Id|Enrollment_Date|Last_Flight_Date|Tier_Code|Agent_Name|State|Country|DOB|Is_Active\n"
    good = tmp_path / "members_20240115.dat"; good.write_text(hdr + "|D|a|123456|20100101|||||USA||A\n")
    r = tmp_path / "redemptions_20240115_001.json"; r.write_text("{}")
    validate_files([good, r], SPEC, red)                       # no exception

    bad_hdr = tmp_path / "members_20240116.dat"; bad_hdr.write_text(hdr.replace("Country", "County"))
    bad_name = tmp_path / "members_2024.dat"; bad_name.write_text(hdr)
    with pytest.raises(ValueError) as e:
        validate_files([bad_hdr, bad_name], SPEC, red)
    assert "header record" in str(e.value) and "members_2024.dat" in str(e.value)
