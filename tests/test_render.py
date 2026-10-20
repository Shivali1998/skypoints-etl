import re

from src.config import ROOT, render_context, render_sql
from src.pipeline.country_splitter import country_statements, seed_ref_sql
from src.pipeline.runner import step_sql


def test_every_step_renders_without_unresolved_placeholders():
    ctx = render_context("20240115")
    for step in ctx["steps"]:
        sql = step_sql(step, ctx)
        assert "{{" not in sql and "{%" not in sql, step["name"]


def test_one_table_per_country_and_each_has_delete_for_moves():
    sql = country_statements("20240115")
    for t in ("TABLE_USA", "TABLE_INDIA", "TABLE_PHILIPPINES", "TABLE_CANADA", "TABLE_AUSTRALIA"):
        assert f"CREATE TABLE IF NOT EXISTS CURATED.{t}" in sql
    assert sql.count("DELETE FROM CURATED.") == 5


def test_country_seed_maps_every_sample_code():
    sql = seed_ref_sql()
    for code in ("USA", "IND", "PHIL", "CAN", "AU"):
        assert f"('{code}'," in sql


def test_dq_covers_every_sample_issue():
    sql = render_sql("sql/dq/member_rules.sql", **render_context("20240115"))
    for rule in ("FIELD_COUNT_MISMATCH", "BAD_DOB", "UNMAPPED_COUNTRY", "BAD_MEMBER_ID_FORMAT",
                 "DUP_MEMBER_IN_FILE", "MISSING_MANDATORY", "BAD_TIER"):
        assert rule in sql


def test_member_id_regex_flags_short_ids_only():
    rx = re.compile(render_context("x")["member_id_regex"])
    assert rx.match("223457") and not rx.match("22345") and not rx.match("2256")


def test_country_split_only_touches_todays_members():
    sql = country_statements("20240115")
    assert sql.count("STAGING.MEMBER_LATEST") >= 10   # merge source + delete source, per country
    assert "FROM CURATED.MEMBER_CURRENT WHERE country_iso3" not in sql   # no whole-table scan
