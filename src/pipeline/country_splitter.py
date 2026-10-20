from src.config import load_yaml, render_sql


def country_statements(file_date: str) -> str:
    """One CREATE-IF-NOT-EXISTS + MERGE + DELETE-moved block per country in config (REF.COUNTRY seed)."""
    out = []
    for c in load_yaml("country_mapping.yaml")["countries"]:
        for tpl in ("country_table.sql.j2", "country_merge.sql.j2"):
            out.append(render_sql(f"sql/transform/templates/{tpl}", table=c["table"], iso3=c["iso3"],
                                  file_date=file_date))
    return "\n".join(out)


def seed_ref_sql() -> str:
    rows = [f"('{code}','{c['iso3']}','{c['name']}','{c['table']}')"
            for c in load_yaml("country_mapping.yaml")["countries"] for code in c["source_codes"]]
    return ("DELETE FROM REF.COUNTRY;\nINSERT INTO REF.COUNTRY (source_code, iso3, country_name, table_name) VALUES\n"
            + ",\n".join(rows) + ";\n")
