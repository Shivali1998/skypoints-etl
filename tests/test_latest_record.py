"""The QUALIFY used in build_member_current.sql, run against DuckDB (which supports QUALIFY)."""
import re

from src.config import ROOT

SQL = (ROOT / "sql/transform/build_member_current.sql").read_text()
QUALIFY = re.search(r"QUALIFY (.*?) = 1;", SQL, re.S).group(1)


def latest(db):
    return db.execute(f"SELECT member_id, country_iso3 FROM s s QUALIFY {QUALIFY} = 1 ORDER BY 1").fetchall()


def test_member_moving_country_keeps_only_newest(db):
    db.execute("CREATE TABLE s(member_id VARCHAR, country_iso3 VARCHAR, file_date DATE, last_flight_date DATE, row_no INT)")
    db.execute("""INSERT INTO s VALUES
        ('1','IND','2024-01-14','2024-01-01',1),
        ('1','CAN','2024-01-15','2024-01-01',1),
        ('2','USA','2024-01-15','2024-01-01',1)""")
    assert latest(db) == [("1", "CAN"), ("2", "USA")]


def test_tie_on_file_and_flight_uses_last_row(db):
    db.execute("CREATE TABLE s(member_id VARCHAR, country_iso3 VARCHAR, file_date DATE, last_flight_date DATE, row_no INT)")
    db.execute("INSERT INTO s VALUES ('1','IND','2024-01-15','2024-01-01',1),('1','USA','2024-01-15','2024-01-01',9)")
    assert latest(db) == [("1", "USA")]


def test_null_flight_date_loses_ties(db):
    db.execute("CREATE TABLE s(member_id VARCHAR, country_iso3 VARCHAR, file_date DATE, last_flight_date DATE, row_no INT)")
    db.execute("INSERT INTO s VALUES ('1','IND','2024-01-15',NULL,9),('1','USA','2024-01-15','2024-01-01',1)")
    assert latest(db) == [("1", "USA")]
