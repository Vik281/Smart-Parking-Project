from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.staticfiles import StaticFiles

app = FastAPI()
frontend_folder = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_folder), name="static")

# This list is deliberately kept in memory for the demo.
parking_locations = [
    {"id": 1, "name": "City Mall Parking", "city": "Delhi", "price": 40, "spots": 10},
    {"id": 2, "name": "Metro Parking", "city": "Delhi", "price": 30, "spots": 5},
]


class BookingRequest(BaseModel):
    name: str
    vehicle_number: str


@app.get("/api/v1/health")
def health_check():
    return {"status": "UP"}


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(frontend_folder / "index.html")


@app.get("/api/v1/locations")
def get_locations():
    return parking_locations


@app.post("/api/v1/locations/{location_id}/book")
def book_spot(location_id: int, booking: BookingRequest):
    for location in parking_locations:
        if location["id"] == location_id:
            if location["spots"] == 0:
                raise HTTPException(status_code=400, detail="No spots available")
            location["spots"] -= 1
            return {
                "message": "Spot booked!",
                "location": location["name"],
                "name": booking.name,
                "vehicle_number": booking.vehicle_number,
                "available_spots": location["spots"],
            }

    raise HTTPException(status_code=404, detail="Parking location not found")
