from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FileCheck:
    ok: bool
    file_date: str | None = None
    problems: tuple = ()


def check_name(name: str, pattern: str) -> FileCheck:
    m = re.match(pattern, name)
    if not m:
        return FileCheck(False, problems=(f"name does not match {pattern}",))
    fd = m.group("file_date")
    try:
        datetime.strptime(fd, "%Y%m%d")
    except ValueError:
        return FileCheck(False, problems=(f"invalid date in file name: {fd}",))
    return FileCheck(True, fd)


def check_member_header(first_line: str, expected_columns: list[str]) -> bool:
    parts = [p.strip().lower() for p in first_line.strip().split("|")]
    return len(parts) > 2 and parts[1] == "h" and parts[2:] == expected_columns


def file_hash(path: str, chunk: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()
