import os
import sqlite3
from datetime import date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "events.db")

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                image TEXT
            )
        """)

def add_event(timestamp, event_type, image):
    with connect() as conn:
        conn.execute(
            "INSERT INTO events(timestamp, event_type, image) VALUES (?, ?, ?)",
            (timestamp, event_type, image)
        )

def get_events(limit=25):
    with connect() as conn:
        rows = conn.execute(
            "SELECT timestamp, event_type, image FROM events ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [dict(row) for row in rows]

def get_stats():
    today = date.today().isoformat()
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        today_count = conn.execute(
            "SELECT COUNT(*) FROM events WHERE substr(timestamp, 1, 10) = ?", (today,)
        ).fetchone()[0]
        last = conn.execute(
            "SELECT timestamp FROM events ORDER BY id DESC LIMIT 1"
        ).fetchone()
    last_time = last["timestamp"][11:19] if last else "--:--:--"
    return {"total_events": total, "today_events": today_count, "last_event_time": last_time}
