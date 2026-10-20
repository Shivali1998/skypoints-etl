"""Config loading and SQL template rendering (shared by the runner and the tests)."""
from pathlib import Path

import jinja2
import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_yaml(name: str) -> dict:
    return yaml.safe_load((ROOT / "config" / name).read_text())


def render_context(file_date: str) -> dict:
    ctx = {"file_date": file_date}
    for f in ("pipeline.yaml", "member_file_spec.yaml", "redemption_spec.yaml"):
        for k, v in load_yaml(f).items():
            # the redemption spec reuses `date_format`; the member spec value is the same
            ctx.setdefault(k, v)
    return ctx


def render_sql(path: str, **ctx) -> str:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT)),
                             undefined=jinja2.StrictUndefined, keep_trailing_newline=True)
    return env.get_template(path).render(**ctx)
