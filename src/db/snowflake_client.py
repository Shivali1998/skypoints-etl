import os


class SnowflakeClient:
    """Thin wrapper around the Snowflake connector (imported lazily so tests and --dry-run need no account)."""

    def __init__(self):
        import snowflake.connector
        kw = dict(account=os.environ["SNOWFLAKE_ACCOUNT"], user=os.environ["SNOWFLAKE_USER"],
                  warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "SKYPOINTS_WH"),
                  database=os.environ.get("SNOWFLAKE_DATABASE", "SKYPOINTS"))
        if os.environ.get("SNOWFLAKE_TOKEN"):  # programmatic access token (no password / MFA prompt)
            kw.update(authenticator="PROGRAMMATIC_ACCESS_TOKEN", token=os.environ["SNOWFLAKE_TOKEN"])
        else:
            kw["password"] = os.environ["SNOWFLAKE_PASSWORD"]
        self.conn = snowflake.connector.connect(**kw)

    def execute(self, sql: str, params: tuple = ()) -> None:
        cur = self.conn.cursor()
        try:
            cur.execute(sql, params or None)
        finally:
            cur.close()

    def execute_script(self, sql: str) -> None:
        """Run several ';'-separated statements, skipping empty or comment-only fragments."""
        for stmt in (s.strip() for s in sql.split(";\n")):
            if any(line.strip() and not line.strip().startswith("--") for line in stmt.splitlines()):
                self.execute(stmt)

    def scalar(self, sql: str):
        cur = self.conn.cursor()
        try:
            return cur.execute(sql).fetchone()[0]
        finally:
            cur.close()
