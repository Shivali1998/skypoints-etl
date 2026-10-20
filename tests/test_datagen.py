from src.config import load_yaml
from src.datagen.generate import generate
from src.ingest.file_checks import check_name


def test_chunks_cover_all_rows_with_one_header_each(tmp_path):
    generate(rows=25, bad_pct=0, file_date="20240118", out=tmp_path, chunks=3, id_start=1000)
    files = sorted(tmp_path.glob("members_20240118_*.dat"))
    assert [f.name for f in files] == [f"members_20240118_00{i}.dat" for i in (1, 2, 3)]
    ids = []
    for f in files:
        lines = f.read_text().splitlines()
        assert lines[0].startswith("|H|")
        ids += [l.split("|")[3] for l in lines[1:]]
    assert len(ids) == 25 and len(set(ids)) == 25 and ids[0] == "101000"
    assert len(list(tmp_path.glob("redemptions_20240118_*.json"))) == 3


def test_chunk_names_pass_file_checks():
    spec = load_yaml("member_file_spec.yaml")
    assert check_name("members_20240118_002.dat", spec["file_name_pattern"]).ok
    assert check_name("members_20240118.dat", spec["file_name_pattern"]).ok
    assert not check_name("members_20240118_2x.dat", spec["file_name_pattern"]).ok


def test_bad_rows_are_generated(tmp_path):
    generate(rows=500, bad_pct=20, file_date="20240118", out=tmp_path)
    lines = (tmp_path / "members_20240118.dat").read_text().splitlines()[1:]
    assert any(len(l.split("|")) != 12 or "ZZZ" in l or "XXX" in l for l in lines)
