import os
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

ROUTES_URL = os.getenv("ROUTES_URL", "http://routes-service:8001")
TELEMETRY_URL = os.getenv("TELEMETRY_URL", "http://telemetry-service:8002")

app = FastAPI(title="SmartBus Gateway", version="1.0")
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}

@app.get("/api/routes")
async def api_routes():
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{ROUTES_URL}/routes")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="routes-service error")
    return r.json()

@app.get("/api/routes/{route_id}")
async def api_route_detail(route_id: int):
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{ROUTES_URL}/routes/{route_id}")
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Route not found")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="routes-service error")
    return r.json()

@app.get("/api/buses")
async def api_buses():
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{TELEMETRY_URL}/buses")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="telemetry-service error")
    return r.json()

@app.get("/api/buses/{bus_id}")
async def api_bus(bus_id: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{TELEMETRY_URL}/buses/{bus_id}")
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Bus not found")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="telemetry-service error")
    return r.json()

@app.post("/api/buses/{bus_id}/update")
async def api_bus_update(bus_id: str, body: dict):
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.post(f"{TELEMETRY_URL}/buses/{bus_id}/update", json=body)
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Bus not found")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="telemetry-service error")
    return r.json()
