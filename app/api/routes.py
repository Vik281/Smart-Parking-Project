from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.parking import (
    ActivityItem,
    BookingCreate,
    BookingOut,
    CancelOut,
    LocationOut,
    StatsOut,
)
from app.services import parking_service

# Routes stay thin: parse the request, call a service, return the result.
router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health_check():
    return {"status": "UP"}


@router.get("/locations", response_model=list[LocationOut])
def get_locations(db: Session = Depends(get_db)):
    return parking_service.list_locations(db)


@router.get("/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    return parking_service.get_stats(db)


@router.get("/activity", response_model=list[ActivityItem])
def get_activity(db: Session = Depends(get_db)):
    return parking_service.recent_activity(db)


@router.post("/locations/{location_id}/book", response_model=BookingOut, status_code=201)
def book_spot(location_id: int, booking: BookingCreate, db: Session = Depends(get_db)):
    return parking_service.book_spot(db, location_id, booking)


@router.delete("/locations/{location_id}/book/{spot_number}", response_model=CancelOut)
def cancel_booking(location_id: int, spot_number: str, db: Session = Depends(get_db)):
    return parking_service.cancel_booking(db, location_id, spot_number)
