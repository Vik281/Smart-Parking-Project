from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Location, Spot

DEMO_LOCATIONS = [
    {"name": "City Mall Parking", "address": "Sector 18, Noida", "price": 40, "rating": 4.5,
     "amenities": ["CCTV", "Covered", "EV Charging"], "prefix": "CM", "spot_count": 10},
    {"name": "Metro Parking", "address": "Rajiv Chowk Metro Station", "price": 30, "rating": 4.1,
     "amenities": ["CCTV", "24x7 Access"], "prefix": "MP", "spot_count": 5},
    {"name": "Airport Parking", "address": "Terminal 3, IGI Airport", "price": 60, "rating": 4.7,
     "amenities": ["Covered", "Valet", "CCTV"], "prefix": "AP", "spot_count": 8},
    {"name": "Tech Park Parking", "address": "DLF Cyber City, Gurugram", "price": 35, "rating": 4.3,
     "amenities": ["EV Charging", "24x7 Access"], "prefix": "TP", "spot_count": 12},
]


def seed_if_empty(db: Session) -> None:
    """Insert demo locations on first run only, so restarts keep existing bookings."""
    if db.scalar(select(Location.id).limit(1)) is not None:
        return

    for data in DEMO_LOCATIONS:
        location = Location(
            name=data["name"],
            address=data["address"],
            price=data["price"],
            rating=data["rating"],
            amenities=data["amenities"],
            spots=[Spot(number=f"{data['prefix']}-{n}") for n in range(1, data["spot_count"] + 1)],
        )
        db.add(location)
    db.commit()
