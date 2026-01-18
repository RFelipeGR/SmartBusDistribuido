import os
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import math


ROUTES_URL = os.getenv("ROUTES_URL", "http://routes-service:8001")
TELEMETRY_URL = os.getenv("TELEMETRY_URL", "http://telemetry-service:8002")

app = FastAPI(title="SmartBus Gateway", version="1.0")
templates = Jinja2Templates(directory="app/templates")


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000  # metros
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2) + math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


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





@app.get("/api/can-i-catch")
async def can_i_catch(
    route_id: int,
    bus_id: str,
    # parámetros simples (puedes dejarlos por defecto)
    bus_speed_mps: float = 8.0,      # ~28.8 km/h
    walk_speed_mps: float = 1.4,     # ~5 km/h
    safety_margin_s: int = 60,       # margen de seguridad (1 min)
    # si no envías user_lat/user_lon, asumimos que estás en la parada (caso UDLA típico)
    user_lat: float | None = None,
    user_lon: float | None = None,
):
    bus_speed_mps = clamp(bus_speed_mps, 2.0, 25.0)
    walk_speed_mps = clamp(walk_speed_mps, 0.5, 3.0)
    safety_margin_s = int(clamp(float(safety_margin_s), 0, 600))

    async with httpx.AsyncClient(timeout=5.0) as client:
        # 1) Ruta + parada
        rr = await client.get(f"{ROUTES_URL}/routes/{route_id}")
        if rr.status_code == 404:
            raise HTTPException(status_code=404, detail="Route not found")
        if rr.status_code != 200:
            raise HTTPException(status_code=502, detail="routes-service error")
        route = rr.json()

        stop_lat = float(route["stop_lat"])
        stop_lon = float(route["stop_lon"])

        # 2) Bus (telemetría)
        rb = await client.get(f"{TELEMETRY_URL}/buses/{bus_id}")
        if rb.status_code == 404:
            raise HTTPException(status_code=404, detail="Bus not found")
        if rb.status_code != 200:
            raise HTTPException(status_code=502, detail="telemetry-service error")
        bus = rb.json()

        bus_lat = float(bus["lat"])
        bus_lon = float(bus["lon"])

    # 3) Distancia bus -> parada
    dist_bus_stop_m = haversine_m(bus_lat, bus_lon, stop_lat, stop_lon)
    eta_bus_s = dist_bus_stop_m / bus_speed_mps

    # 4) Distancia usuario -> parada (si no hay user_lat/lon, asumimos ya estás en la parada)
    if user_lat is None or user_lon is None:
        dist_user_stop_m = 0.0
        eta_user_s = 0.0
        user_mode = "ASSUMED_AT_STOP"
    else:
        dist_user_stop_m = haversine_m(float(user_lat), float(user_lon), stop_lat, stop_lon)
        eta_user_s = dist_user_stop_m / walk_speed_mps
        user_mode = "USER_LOCATION"

    # 5) Decisión: alcanzas si llegas + margen antes que el bus
    can_catch = (eta_user_s + safety_margin_s) < eta_bus_s

    # Mensaje claro tipo “sal apresurado / sal tranquilo”
    # Si el bus llega en menos de 2 min => probablemente está por pasar
    if eta_bus_s <= 120:
        decision = "YA_MUY_CERCA"
        msg = "El bus está por pasar. Apúrate."
    else:
        decision = "ALCANZAS" if can_catch else "NO_ALCANZAS"
        msg = "Sí alcanzas. Puedes salir tranquilo." if can_catch else "No alcanzas con ese margen. Debes apurarte o esperar el siguiente."

    return {
        "route_id": route_id,
        "bus_id": bus_id,
        "stop": {"lat": stop_lat, "lon": stop_lon},
        "bus": {"lat": bus_lat, "lon": bus_lon, "last_updated_utc": bus.get("last_updated_utc")},
        "user_mode": user_mode,
        "distance_bus_to_stop_m": round(dist_bus_stop_m, 2),
        "eta_bus_seconds": round(eta_bus_s, 1),
        "distance_user_to_stop_m": round(dist_user_stop_m, 2),
        "eta_user_seconds": round(eta_user_s, 1),
        "bus_speed_mps": bus_speed_mps,
        "walk_speed_mps": walk_speed_mps,
        "safety_margin_s": safety_margin_s,
        "can_catch": can_catch,
        "decision": decision,
        "message": msg,
    }
