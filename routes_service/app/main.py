from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from .db import init_db, get_conn

app = FastAPI(title="Routes Service", version="1.0")

class RouteOut(BaseModel):
    id: int
    origin: str
    destination: str
    duration_minutes: int
    price_usd: float
    status: str
    stop_lat: float
    stop_lon: float

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok", "service": "routes-service"}

@app.get("/routes", response_model=List[RouteOut])
def list_routes():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM routes ORDER BY id;").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/routes/{route_id}", response_model=RouteOut)
def get_route(route_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM routes WHERE id = ?;", (route_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Route not found")
    return dict(row)
