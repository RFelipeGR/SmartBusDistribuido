import sqlite3
from pathlib import Path

DB_PATH = Path("/app/routes.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            price_usd REAL NOT NULL,
            status TEXT NOT NULL
        );
    """)
    conn.commit()

    # Seed si está vacío
    cur.execute("SELECT COUNT(*) as c FROM routes;")
    if cur.fetchone()["c"] == 0:
        cur.executemany("""
            INSERT INTO routes (origin, destination, duration_minutes, price_usd, status)
            VALUES (?, ?, ?, ?, ?);
        """, [
            ("UDLA", "Cumbayá", 25, 0.35, "ACTIVE"),
            ("UDLA", "Quito Centro", 55, 0.50, "ACTIVE"),
            ("UDLA", "Valle de los Chillos", 65, 0.60, "ACTIVE"),
        ])
        conn.commit()

    conn.close()
