from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict
from datetime import datetime, timezone
import os

from .messaging import RabbitPublisher

app = FastAPI(title="Telemetry Service", version="1.0")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "telemetry.events")

publisher = RabbitPublisher(RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASS, RABBITMQ_QUEUE)

# Estado en memoria (suficiente para MVP)
STATE: Dict[str, dict] = {
    "BUS-001": {"lat": -0.1807, "lon": -78.4678, "occupancy": 12, "last_updated_utc": None},
    "BUS-002": {"lat": -0.1900, "lon": -78.4800, "occupancy": 5, "last_updated_utc": None},
}

class TelemetryUpdate(BaseModel):
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    occupancy: int = Field(..., ge=0, le=100, description="Occupancy percentage or count")
    
@app.get("/health")
def health():
    return {"status": "ok", "service": "telemetry-service"}

@app.get("/buses")
def list_buses():
    return {"buses": list(STATE.keys())}

@app.get("/buses/{bus_id}")
def get_bus(bus_id: str):
    if bus_id not in STATE:
        raise HTTPException(status_code=404, detail="Bus not found")
    return {"bus_id": bus_id, **STATE[bus_id]}

@app.post("/buses/{bus_id}/update")
def update_bus(bus_id: str, body: TelemetryUpdate):
    if bus_id not in STATE:
        raise HTTPException(status_code=404, detail="Bus not found")

    now = datetime.now(timezone.utc).isoformat()
    STATE[bus_id] = {
        "lat": body.lat,
        "lon": body.lon,
        "occupancy": body.occupancy,
        "last_updated_utc": now,
    }

    # Publica evento async (coordinación + mensajería)
    publisher.publish_event(
        event_type="bus_telemetry_updated",
        payload={"bus_id": bus_id, **STATE[bus_id]},
    )

    return {"ok": True, "bus_id": bus_id, **STATE[bus_id]}
