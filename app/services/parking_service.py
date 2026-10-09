from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Booking, Location, Spot
from app.schemas.parking import (
    ActivityItem,
    BookingCreate,
    BookingOut,
    CancelOut,
    LocationOut,
    StatsOut,
)
from app.services.errors import ConflictError, NotFoundError

MAX_ACTIVITY_ITEMS = 8


def _get_location(db: Session, location_id: int) -> Location:
    location = db.get(Location, location_id)
    if location is None:
        raise NotFoundError("Parking location not found")
    return location


def _get_spot(db: Session, location_id: int, spot_number: str) -> Spot:
    spot = db.scalar(
        select(Spot).where(Spot.location_id == location_id, Spot.number == spot_number)
    )
    if spot is None:
        raise NotFoundError("Invalid parking spot")
    return spot


def _active_booking_for(db: Session, spot_id: int) -> Booking | None:
    return db.scalar(
        select(Booking).where(Booking.spot_id == spot_id, Booking.status == "active")
    )


def _available_spots(db: Session, location: Location) -> int:
    booked = db.scalar(
        select(func.count(Booking.id))
        .join(Spot)
        .where(Spot.location_id == location.id, Booking.status == "active")
    )
    return len(location.spots) - booked


def list_locations(db: Session) -> list[LocationOut]:
    # Two queries total, however many locations exist (avoids the N+1 query problem).
    locations = db.scalars(
        select(Location).options(selectinload(Location.spots)).order_by(Location.id)
    ).all()
    booked_spot_ids = set(
        db.scalars(select(Booking.spot_id).where(Booking.status == "active")).all()
    )

    result = []
    for location in locations:
        spot_numbers = [spot.number for spot in location.spots]
        booked = [spot.number for spot in location.spots if spot.id in booked_spot_ids]
        result.append(LocationOut(
            id=location.id,
            name=location.name,
            address=location.address,
            price=location.price,
            rating=location.rating,
            amenities=location.amenities,
            spot_numbers=spot_numbers,
            booked_spots=booked,
            total_spots=len(spot_numbers),
            spots=len(spot_numbers) - len(booked),
        ))
    return result


def get_stats(db: Session) -> StatsOut:
    location_count = db.scalar(select(func.count(Location.id)))
    total_spots = db.scalar(select(func.count(Spot.id)))
    booked_spots = db.scalar(select(func.count(Booking.id)).where(Booking.status == "active"))
    avg_price = db.scalar(select(func.avg(Location.price))) or 0
    return StatsOut(
        locations=location_count,
        total_spots=total_spots,
        available_spots=total_spots - booked_spots,
        booked_spots=booked_spots,
        avg_price=round(avg_price, 2),
    )


def recent_activity(db: Session) -> list[ActivityItem]:
    """The feed is derived from the bookings table rather than stored separately,
    so it can never disagree with the real booking data."""
    recent_bookings = db.scalars(
        select(Booking)
        .options(selectinload(Booking.spot).selectinload(Spot.location))
        .order_by(func.coalesce(Booking.cancelled_at, Booking.created_at).desc())
        .limit(MAX_ACTIVITY_ITEMS)
    ).all()

    events = []
    for booking in recent_bookings:
        common = {"location": booking.spot.location.name, "spot_number": booking.spot.number}
        events.append(ActivityItem(type="booked", at=booking.created_at, **common))
        if booking.cancelled_at:
            events.append(ActivityItem(type="cancelled", at=booking.cancelled_at, **common))

    events.sort(key=lambda event: event.at, reverse=True)
    return events[:MAX_ACTIVITY_ITEMS]


def book_spot(db: Session, location_id: int, data: BookingCreate) -> BookingOut:
    location = _get_location(db, location_id)
    spot = _get_spot(db, location_id, data.spot_number)

    # Fast, friendly check for the common case...
    if _active_booking_for(db, spot.id):
        raise ConflictError("This spot is already booked")

    booking = Booking(spot_id=spot.id, name=data.name, vehicle_number=data.vehicle_number)
    db.add(booking)
    try:
        db.commit()
    except IntegrityError:
        # ...but if two requests pass the check at the same moment, the unique
        # index rejects the second insert. The database is the final authority.
        db.rollback()
        raise ConflictError("This spot is already booked")

    return BookingOut(
        message="Spot booked!",
        booking_id=booking.id,
        location=location.name,
        name=booking.name,
        vehicle_number=booking.vehicle_number,
        spot_number=spot.number,
        available_spots=_available_spots(db, location),
    )


def cancel_booking(db: Session, location_id: int, spot_number: str) -> CancelOut:
    location = _get_location(db, location_id)
    spot = _get_spot(db, location_id, spot_number)

    booking = _active_booking_for(db, spot.id)
    if booking is None:
        raise NotFoundError("No booking found for this spot")

    # Soft delete: keep the row for history and the activity feed.
    booking.status = "cancelled"
    booking.cancelled_at = datetime.now()
    db.commit()

    return CancelOut(
        message="Booking cancelled",
        location=location.name,
        spot_number=spot.number,
        available_spots=_available_spots(db, location),
    )
