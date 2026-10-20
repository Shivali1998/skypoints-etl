"""AGE and STALE_MEMBER expressions come from the same Jinja macros the Snowflake SQL uses."""
import jinja2
import pytest

from src.config import ROOT

ENV = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT)))
M = ENV.get_template("sql/macros/derived.sql.j2").module


def q(db, expr):
    return db.execute(f"SELECT {expr}").fetchone()[0]


@pytest.mark.parametrize("dob,asof,expected", [
    ("1985-05-03", "2024-05-02", 38),   # birthday not yet reached -> naive DATEDIFF(year) would say 39
    ("1985-05-03", "2024-05-03", 39),   # birthday today
    ("1985-05-03", "2024-12-31", 39),
    ("2000-02-29", "2023-02-28", 22),   # leap-day birthday, day before 28 Feb anniversary
    ("2000-02-29", "2023-03-01", 23),
])
def test_age(db, dob, asof, expected):
    assert q(db, M.age(f"DATE '{dob}'", f"DATE '{asof}'")) == expected


@pytest.mark.parametrize("flight,expected", [
    ("2024-04-16", "N"),   # exactly 90 days -> not stale (rule is > 90)
    ("2024-04-15", "Y"),   # 91 days
    ("2012-10-13", "Y"),
])
def test_stale(db, flight, expected):
    assert q(db, M.stale(f"DATE '{flight}'", "DATE '2024-07-15'", 90)) == expected


def test_stale_null_flight_is_null(db):
    assert q(db, M.stale("CAST(NULL AS DATE)", "DATE '2024-07-15'", 90)) is None
