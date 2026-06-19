import sqlite3


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS flux_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bucket_ts INTEGER NOT NULL UNIQUE,
            energy_in REAL NOT NULL,
            energy_out REAL NOT NULL,
            buffer REAL NOT NULL,
            capacity REAL
        );

        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            ts INTEGER NOT NULL,
            items_json TEXT NOT NULL,
            craftables_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            item TEXT NOT NULL,
            label TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        """
    )
    conn.commit()
