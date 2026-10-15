from fastapi import APIRouter, Depends
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.parking import (
    ActivityItem,
    BookingCreate,
    BookingOut,
    CancelOut,
    LocationOut,
    SpotBooking,
    StatsOut,
)
from app.services import parking_service

# Routes stay thin: parse the request, call a service, return the result.
router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health_check():
    return {"status": "UP"}


@router.get("/locations", response_model=list[LocationOut])
def get_locations(
    start: AwareDatetime | None = None,
    end: AwareDatetime | None = None,
    db: Session = Depends(get_db),
):
    """Availability for the window [start, end); defaults to the next hour."""
    return parking_service.list_locations(db, start, end)


@router.get(
    "/locations/{location_id}/spots/{spot_number}/bookings",
    response_model=list[SpotBooking],
)
def get_spot_schedule(location_id: int, spot_number: str, db: Session = Depends(get_db)):
    return parking_service.spot_schedule(db, location_id, spot_number)


@router.get("/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    return parking_service.get_stats(db)


@router.get("/activity", response_model=list[ActivityItem])
def get_activity(db: Session = Depends(get_db)):
    return parking_service.recent_activity(db)


@router.post("/locations/{location_id}/book", response_model=BookingOut, status_code=201)
def book_spot(location_id: int, booking: BookingCreate, db: Session = Depends(get_db)):
    return parking_service.book_spot(db, location_id, booking)


# A spot can now have many bookings, so a cancellation names the booking itself.
@router.delete("/bookings/{booking_id}", response_model=CancelOut)
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    return parking_service.cancel_booking(db, booking_id)
