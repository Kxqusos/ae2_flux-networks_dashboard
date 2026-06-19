import sqlite3

from app.db import get_connection, init_db


def test_init_db_creates_tables(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = get_connection(db_path)
    init_db(conn)

    tables = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"flux_samples", "inventory", "orders"} <= tables


def test_get_connection_returns_row_factory(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = get_connection(db_path)
    assert conn.row_factory is sqlite3.Row


def test_flux_samples_bucket_ts_unique(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = get_connection(db_path)
    init_db(conn)

    conn.execute(
        "INSERT INTO flux_samples (bucket_ts, energy_in, energy_out, buffer, capacity) "
        "VALUES (1000, 1.0, 2.0, 3.0, 4.0)"
    )
    conn.commit()

    try:
        conn.execute(
            "INSERT INTO flux_samples (bucket_ts, energy_in, energy_out, buffer, capacity) "
            "VALUES (1000, 9.0, 9.0, 9.0, 9.0)"
        )
        conn.commit()
        assert False, "expected IntegrityError"
    except sqlite3.IntegrityError:
        pass
