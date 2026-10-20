"""python -m src.pipeline.runner --date 20240115 [--dry-run]"""
from __future__ import annotations

import argparse
import uuid
from datetime import datetime

from src.config import ROOT, load_yaml, render_context, render_sql
from src.pipeline.country_splitter import country_statements, seed_ref_sql


def step_sql(step: dict, ctx: dict) -> str:
    if step.get("generator") == "country_split":
        return country_statements(ctx["file_date"])
    return render_sql(step["sql"], **ctx)


def run(file_date: str, dry_run: bool = False, data_dir: str = "data/sample") -> None:
    ctx = render_context(file_date)
    run_id = uuid.uuid4().hex[:12]
    client = None
    if not dry_run:
        from src.db.snowflake_client import SnowflakeClient
        client = SnowflakeClient()
        for ddl in sorted((ROOT / "sql/ddl").glob("*.sql")):
            client.execute_script(ddl.read_text())
        client.execute_script(seed_ref_sql())
        from src.ingest.uploader import put_files
        files = [ROOT / data_dir / f"members_{file_date}.dat", ROOT / data_dir / f"redemptions_{file_date}.json"]
        put_files(client, [f for f in files if f.exists()])
    for step in ctx["steps"]:
        sql = step_sql(step, ctx)
        if dry_run:
            print(f"-- === {step['name']} ===\n{sql}")
            continue
        started = datetime.utcnow()
        try:
            affected = client.execute_script(sql)
            status, msg = "OK", None
        except Exception as exc:  # stop the run at the failing step; rerun is safe (idempotent steps)
            status, msg, affected = "FAILED", str(exc)[:500], None
        client.execute_script(
            f"INSERT INTO AUDIT.ETL_RUN_LOG (run_id,file_date,step,status,rows_out,started_ts,ended_ts,message) "
            f"SELECT '{run_id}', TO_DATE('{file_date}','YYYYMMDD'), '{step['name']}', '{status}', "
            f"{affected if affected is not None else 'NULL'}, '{started.isoformat()}', CURRENT_TIMESTAMP(), "
            f"{'NULL' if msg is None else chr(39) + msg.replace(chr(39), chr(39) * 2) + chr(39)}")
        if status == "FAILED":
            raise SystemExit(f"step {step['name']} failed: {msg}")
    if client:
        # Reconciliation: every raw detail row is either in staging or explained; staging rows == raw rows.
        raw = client.scalar(f"SELECT COUNT(*) FROM RAW.RAW_MEMBERS WHERE rec_type='D' AND file_date=TO_DATE('{file_date}','YYYYMMDD')")
        stg = client.scalar(f"SELECT COUNT(*) FROM STAGING.STG_MEMBERS WHERE file_date=TO_DATE('{file_date}','YYYYMMDD')")
        if raw != stg:
            raise SystemExit(f"reconciliation failed: raw={raw} staging={stg}")
        print(f"run {run_id} OK: {raw} member rows reconciled")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="file_date YYYYMMDD")
    ap.add_argument("--dry-run", action="store_true", help="print rendered SQL, do not connect")
    ap.add_argument("--data-dir", default="data/sample")
    a = ap.parse_args()
    run(a.date, a.dry_run, a.data_dir)
