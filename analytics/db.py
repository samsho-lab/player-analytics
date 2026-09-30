import csv
import sqlite3
from pathlib import Path

QUERIES = Path(__file__).parent / "queries"


def sql(name: str) -> str:
    return (QUERIES / f"{name}.sql").read_text()


def load(rows, path: str = ":memory:") -> sqlite3.Connection:
    """Load raw event rows (dicts) into SQLite and build the cleaned tables."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        DROP TABLE IF EXISTS raw_events;
        CREATE TABLE raw_events (
            event_id  TEXT NOT NULL,
            player_id TEXT NOT NULL,
            event     TEXT NOT NULL,
            ts        TEXT NOT NULL,
            variant   TEXT
        );
    """)
    conn.executemany(
        "INSERT INTO raw_events VALUES (:event_id, :player_id, :event, :ts, :variant)",
        rows,
    )
    conn.executescript(sql("clean"))
    return conn


def load_csv(csv_path: str, db_path: str = ":memory:") -> sqlite3.Connection:
    with open(csv_path, newline="") as f:
        return load(csv.DictReader(f), db_path)


def query(conn: sqlite3.Connection, name: str) -> list[dict]:
    return [dict(r) for r in conn.execute(sql(name))]


def data_quality(conn: sqlite3.Connection) -> dict:
    raw = conn.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    unique = conn.execute("SELECT COUNT(DISTINCT event_id) FROM raw_events").fetchone()[0]
    clean = conn.execute("SELECT COUNT(*) FROM clean_events").fetchone()[0]
    return {
        "raw_events": raw,
        "duplicates_removed": raw - unique,
        "other_rows_removed": unique - clean,  # unknown names + events before install
        "clean_events": clean,
        "players": conn.execute("SELECT COUNT(*) FROM players").fetchone()[0],
    }
