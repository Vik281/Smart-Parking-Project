from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.staticfiles import StaticFiles

app = FastAPI(title="ParkShare API")
frontend_folder = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_folder), name="static")


def make_spots(prefix: str, count: int) -> list[str]:
    return [f"{prefix}-{number}" for number in range(1, count + 1)]


# Kept in memory for the demo; resets whenever the server restarts.
parking_locations = [
    {
        "id": 1,
        "name": "City Mall Parking",
        "address": "Sector 18, Noida",
        "price": 40,
        "rating": 4.5,
        "amenities": ["CCTV", "Covered", "EV Charging"],
        "spot_numbers": make_spots("CM", 10),
        "bookings": {},
    },
    {
        "id": 2,
        "name": "Metro Parking",
        "address": "Rajiv Chowk Metro Station",
        "price": 30,
        "rating": 4.1,
        "amenities": ["CCTV", "24x7 Access"],
        "spot_numbers": make_spots("MP", 5),
        "bookings": {},
    },
    {
        "id": 3,
        "name": "Airport Parking",
        "address": "Terminal 3, IGI Airport",
        "price": 60,
        "rating": 4.7,
        "amenities": ["Covered", "Valet", "CCTV"],
        "spot_numbers": make_spots("AP", 8),
        "bookings": {},
    },
    {
        "id": 4,
        "name": "Tech Park Parking",
        "address": "DLF Cyber City, Gurugram",
        "price": 35,
        "rating": 4.3,
        "amenities": ["EV Charging", "24x7 Access"],
        "spot_numbers": make_spots("TP", 12),
        "bookings": {},
    },
]

# Most recent booking/cancellation events first, for the live activity feed.
recent_activity: list[dict] = []

MAX_ACTIVITY_ITEMS = 8


class BookingRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    vehicle_number: str = Field(min_length=1, max_length=20)
    spot_number: str


def find_location(location_id: int) -> dict:
    for location in parking_locations:
        if location["id"] == location_id:
            return location
    raise HTTPException(status_code=404, detail="Parking location not found")


def serialize_location(location: dict) -> dict:
    total_spots = len(location["spot_numbers"])
    booked_spots = len(location["bookings"])
    return {
        "id": location["id"],
        "name": location["name"],
        "address": location["address"],
        "price": location["price"],
        "rating": location["rating"],
        "amenities": location["amenities"],
        "spot_numbers": location["spot_numbers"],
        "booked_spots": list(location["bookings"].keys()),
        "total_spots": total_spots,
        "spots": total_spots - booked_spots,
    }


def log_activity(event_type: str, location: dict, spot_number: str) -> None:
    recent_activity.insert(0, {
        "type": event_type,
        "location": location["name"],
        "spot_number": spot_number,
        "at": datetime.now().isoformat(timespec="seconds"),
    })
    del recent_activity[MAX_ACTIVITY_ITEMS:]


@app.get("/api/v1/health")
def health_check():
    return {"status": "UP"}


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(frontend_folder / "index.html")


@app.get("/api/v1/locations")
def get_locations():
    return [serialize_location(location) for location in parking_locations]


@app.get("/api/v1/stats")
def get_stats():
    total_spots = sum(len(location["spot_numbers"]) for location in parking_locations)
    booked_spots = sum(len(location["bookings"]) for location in parking_locations)
    avg_price = sum(location["price"] for location in parking_locations) / len(parking_locations)
    return {
        "locations": len(parking_locations),
        "total_spots": total_spots,
        "available_spots": total_spots - booked_spots,
        "booked_spots": booked_spots,
        "avg_price": round(avg_price, 2),
    }


@app.get("/api/v1/activity")
def get_activity():
    return recent_activity


@app.post("/api/v1/locations/{location_id}/book")
def book_spot(location_id: int, booking: BookingRequest):
    location = find_location(location_id)

    if booking.spot_number not in location["spot_numbers"]:
        raise HTTPException(status_code=400, detail="Invalid parking spot")
    if booking.spot_number in location["bookings"]:
        raise HTTPException(status_code=400, detail="This spot is already booked")

    location["bookings"][booking.spot_number] = {
        "name": booking.name.strip(),
        "vehicle_number": booking.vehicle_number.strip().upper(),
    }
    log_activity("booked", location, booking.spot_number)

    return {
        "message": "Spot booked!",
        "location": location["name"],
        "name": booking.name.strip(),
        "vehicle_number": booking.vehicle_number.strip().upper(),
        "spot_number": booking.spot_number,
        "available_spots": len(location["spot_numbers"]) - len(location["bookings"]),
    }


@app.delete("/api/v1/locations/{location_id}/book/{spot_number}")
def cancel_booking(location_id: int, spot_number: str):
    location = find_location(location_id)

    if spot_number not in location["bookings"]:
        raise HTTPException(status_code=404, detail="No booking found for this spot")

    del location["bookings"][spot_number]
    log_activity("cancelled", location, spot_number)

    return {
        "message": "Booking cancelled",
        "location": location["name"],
        "spot_number": spot_number,
        "available_spots": len(location["spot_numbers"]) - len(location["bookings"]),
    }
