import duckdb
import pytest


@pytest.fixture
def db():
    con = duckdb.connect()
    yield con
    con.close()
