from pathlib import Path


def put_files(client, paths, stage: str = "@RAW.SKYPOINTS_STAGE") -> None:
    """PUT local files to the stage uncompressed so COPY paths match the file names."""
    for p in paths:
        client.execute_script(f"PUT 'file://{Path(p).resolve()}' {stage} AUTO_COMPRESS=FALSE OVERWRITE=TRUE")
