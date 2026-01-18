import sqlite3
from pathlib import Path

DB_PATH = Path("/app/routes.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table});")
    cols = [r[1] for r in cur.fetchall()]
    return column in cols

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

    # Migración simple: agregar columnas de parada
    if not _column_exists(conn, "routes", "stop_lat"):
        cur.execute("ALTER TABLE routes ADD COLUMN stop_lat REAL;")
    if not _column_exists(conn, "routes", "stop_lon"):
        cur.execute("ALTER TABLE routes ADD COLUMN stop_lon REAL;")
    conn.commit()

    # Seed si está vacío
    cur.execute("SELECT COUNT(*) as c FROM routes;")
    if cur.fetchone()["c"] == 0:
        # Parada UDLA (ajusta si quieres)
        stop_lat, stop_lon = -0.1875, -78.4350

        cur.executemany("""
            INSERT INTO routes (origin, destination, duration_minutes, price_usd, status, stop_lat, stop_lon)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, [
            ("UDLA", "Cumbayá", 25, 0.35, "ACTIVE", stop_lat, stop_lon),
            ("UDLA", "Quito Centro", 55, 0.50, "ACTIVE", stop_lat, stop_lon),
            ("UDLA", "Valle de los Chillos", 65, 0.60, "ACTIVE", stop_lat, stop_lon),
        ])
        conn.commit()

    # Si ya existían rutas, asegurar coordenadas no nulas
    cur.execute("""
        UPDATE routes
        SET stop_lat = COALESCE(stop_lat, -0.1875),
            stop_lon = COALESCE(stop_lon, -78.4350);
    """)
    conn.commit()

    conn.close()
