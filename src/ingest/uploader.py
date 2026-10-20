from pathlib import Path


def clear_day(client, file_date: str, stage: str = "@RAW.SKYPOINTS_STAGE") -> None:
    """Remove any earlier upload of this file_date (plain or .gz) so a rerun can never load a file twice."""
    client.execute_script(f"REMOVE {stage} PATTERN='.*(members|redemptions)_{file_date}.*'")


def put_files(client, paths, stage: str = "@RAW.SKYPOINTS_STAGE") -> None:
    """PUT local files gzip-compressed (as production feeds would be); several files upload in parallel."""
    for p in paths:
        client.execute_script(
            f"PUT 'file://{Path(p).resolve()}' {stage} AUTO_COMPRESS=TRUE OVERWRITE=TRUE PARALLEL=8")
