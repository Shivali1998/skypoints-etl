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
