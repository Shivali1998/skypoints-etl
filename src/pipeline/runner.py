"""Daily pipeline.  python -m src.pipeline.runner --date 20240115 [--data-dir data/sample] [--dry-run]

Order of work: set up tables -> check and upload the day's files -> run each SQL step in
config/pipeline.yaml (timed and logged) -> check raw rows == staged rows.
"""
from __future__ import annotations

import argparse
import time
import uuid

from src.config import ROOT, load_yaml, render_context, render_sql
from src.db.snowflake_client import SnowflakeClient
from src.ingest.file_checks import validate_files
from src.ingest.uploader import clear_day, put_files
from src.pipeline.country_splitter import country_statements, seed_ref_sql


def step_sql(step: dict, ctx: dict) -> str:
    """SQL text for one step: a rendered .sql file, or the generated per-country statements."""
    if step.get("generator") == "country_split":
        return country_statements(ctx["file_date"])
    return render_sql(step["sql"], **ctx)


def set_up(client: SnowflakeClient) -> None:
    """Create database objects if missing and load the country mapping. Safe to run every day."""
    for ddl in sorted((ROOT / "sql/ddl").glob("*.sql")):
        client.execute_script(ddl.read_text())
    client.execute_script(seed_ref_sql())


def upload_inputs(client: SnowflakeClient, file_date: str, data_dir: str) -> None:
    """Find the day's member and redemption files (all chunks), check them, replace any earlier upload."""
    folder = ROOT / data_dir
    files = sorted(folder.glob(f"members_{file_date}*.dat")) + sorted(folder.glob(f"redemptions_{file_date}*.json"))
    if not files:
        raise SystemExit(f"no input files for {file_date} in {folder}")
    validate_files(files, load_yaml("member_file_spec.yaml"), load_yaml("redemption_spec.yaml"))
    clear_day(client, file_date)
    put_files(client, files)


def run_step(client: SnowflakeClient, run_id: str, file_date: str, step: dict, ctx: dict) -> None:
    """Run one step, print and log its time, and stop the whole run if it fails."""
    start, error = time.perf_counter(), None
    try:
        client.execute_script(step_sql(step, ctx))
    except Exception as exc:  # the log row is written first, then the run stops; a rerun is safe
        error = str(exc)[:500]
    seconds = time.perf_counter() - start
    status = "FAILED" if error else "OK"
    print(f"{step['name']:<24}{status:<7}{seconds:8.1f}s")
    client.execute(
        "INSERT INTO AUDIT.ETL_RUN_LOG (run_id, file_date, step, status, elapsed_s, message) "
        "SELECT %s, TO_DATE(%s, 'YYYYMMDD'), %s, %s, %s, %s",
        (run_id, file_date, step["name"], status, round(seconds, 2), error))
    if error:
        raise SystemExit(f"step {step['name']} failed: {error}")


def reconcile(client: SnowflakeClient, file_date: str) -> int:
    """Every detail row in RAW must also be in STAGING (bad rows are flagged in DQ_REJECTS, not dropped)."""
    day = f"file_date = TO_DATE('{file_date}', 'YYYYMMDD')"
    raw = client.scalar(f"SELECT COUNT(*) FROM RAW.RAW_MEMBERS WHERE rec_type = 'D' AND {day}")
    staged = client.scalar(f"SELECT COUNT(*) FROM STAGING.STG_MEMBERS WHERE {day}")
    if raw != staged:
        raise SystemExit(f"reconciliation failed: raw={raw} staged={staged}")
    return raw


def run(file_date: str, dry_run: bool = False, data_dir: str = "data/sample") -> None:
    ctx = render_context(file_date)
    if dry_run:  # print the SQL of every step, touch nothing
        for step in ctx["steps"]:
            print(f"-- === {step['name']} ===\n{step_sql(step, ctx)}")
        return
    client = SnowflakeClient()
    run_id = uuid.uuid4().hex[:12]
    set_up(client)
    upload_inputs(client, file_date, data_dir)
    for step in ctx["steps"]:
        run_step(client, run_id, file_date, step, ctx)
    print(f"run {run_id} OK: {reconcile(client, file_date)} member rows reconciled")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="file_date YYYYMMDD")
    ap.add_argument("--data-dir", default="data/sample")
    ap.add_argument("--dry-run", action="store_true", help="print rendered SQL, do not connect")
    a = ap.parse_args()
    run(a.date, a.dry_run, a.data_dir)
