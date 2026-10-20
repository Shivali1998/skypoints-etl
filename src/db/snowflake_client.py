import os


class SnowflakeClient:
    """Thin wrapper; the connector is imported lazily so tests and --dry-run need no account."""

    def __init__(self):
        import snowflake.connector
        self.conn = snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"], user=os.environ["SNOWFLAKE_USER"],
            password=os.environ["SNOWFLAKE_PASSWORD"], warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "SKYPOINTS_WH"),
            database=os.environ.get("SNOWFLAKE_DATABASE", "SKYPOINTS"))

    def execute_script(self, sql: str) -> int:
        """Run ';'-separated statements; return rows affected by the last DML statement."""
        affected = 0
        for stmt in (s.strip() for s in sql.split(";\n")):
            if not any(l.strip() and not l.strip().startswith("--") for l in stmt.splitlines()):
                continue  # empty or comment-only fragment
            cur = self.conn.cursor()
            try:
                cur.execute(stmt)
                if cur.rowcount is not None and cur.rowcount >= 0:
                    affected = cur.rowcount
            finally:
                cur.close()
        return affected

    def scalar(self, sql: str):
        cur = self.conn.cursor()
        try:
            return cur.execute(sql).fetchone()[0]
        finally:
            cur.close()
