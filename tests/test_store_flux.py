from app.db import get_connection, init_db
from app.models import FluxPayload
from app.store import get_flux_history, prune_flux_samples, record_flux_sample


def _conn(tmp_path):
    conn = get_connection(str(tmp_path / "test.db"))
    init_db(conn)
    return conn


def test_record_flux_sample_inserts_new_bucket(tmp_path):
    conn = _conn(tmp_path)
    payload = FluxPayload(energy_in=10.0, energy_out=5.0, buffer=100.0, capacity=200.0)

    record_flux_sample(conn, payload, now_ts=3700)  # bucket 0 (3700 % 3600 = 100)

    history = get_flux_history(conn)
    assert len(history) == 1
    assert history[0]["bucket_ts"] == 3600
    assert history[0]["energy_in"] == 10.0


def test_record_flux_sample_dedupes_same_bucket(tmp_path):
    conn = _conn(tmp_path)
    first = FluxPayload(energy_in=10.0, energy_out=5.0, buffer=100.0)
    second = FluxPayload(energy_in=99.0, energy_out=99.0, buffer=99.0)

    record_flux_sample(conn, first, now_ts=3700)
    record_flux_sample(conn, second, now_ts=3650)  # same bucket (3600)

    history = get_flux_history(conn)
    assert len(history) == 1
    assert history[0]["energy_in"] == 10.0  # first write wins, second is a no-op


def test_record_flux_sample_creates_new_bucket_next_hour(tmp_path):
    conn = _conn(tmp_path)
    record_flux_sample(conn, FluxPayload(energy_in=1.0, energy_out=1.0, buffer=1.0), now_ts=3700)
    record_flux_sample(conn, FluxPayload(energy_in=2.0, energy_out=2.0, buffer=2.0), now_ts=7300)

    history = get_flux_history(conn)
    assert [row["bucket_ts"] for row in history] == [3600, 7200]


def test_get_flux_history_orders_ascending(tmp_path):
    conn = _conn(tmp_path)
    record_flux_sample(conn, FluxPayload(energy_in=2.0, energy_out=2.0, buffer=2.0), now_ts=7300)
    record_flux_sample(conn, FluxPayload(energy_in=1.0, energy_out=1.0, buffer=1.0), now_ts=3700)

    history = get_flux_history(conn)
    assert [row["bucket_ts"] for row in history] == [3600, 7200]


def test_prune_flux_samples_removes_old_rows(tmp_path):
    conn = _conn(tmp_path)
    record_flux_sample(conn, FluxPayload(energy_in=1.0, energy_out=1.0, buffer=1.0), now_ts=3700)
    record_flux_sample(conn, FluxPayload(energy_in=2.0, energy_out=2.0, buffer=2.0), now_ts=99999999)

    prune_flux_samples(conn, cutoff_ts=99999999 - 3600)

    history = get_flux_history(conn)
    assert len(history) == 1
    assert history[0]["bucket_ts"] != 3600
