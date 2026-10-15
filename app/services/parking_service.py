import math
from datetime import datetime, timedelta

from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.models import Booking, Location, Spot
from app.schemas.parking import (
    ActivityItem,
    BookingCreate,
    BookingOut,
    CancelOut,
    LocationOut,
    SpotBooking,
    StatsOut,
)
from app.services.errors import BadRequestError, ConflictError, NotFoundError
from app.timeutils import to_db_time, utc_now

MAX_ACTIVITY_ITEMS = 8
DEFAULT_WINDOW = timedelta(hours=1)
MAX_DAYS_AHEAD = 30
# The UI rounds the start time, and a request takes a moment to arrive, so a
# start time a few minutes in the past is still accepted.
PAST_START_GRACE = timedelta(minutes=5)


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


def _overlaps(start: datetime, end: datetime):
    """SQL condition: an active booking that overlaps [start, end).

    Two intervals overlap exactly when each one starts before the other ends.
    Because the intervals are half-open, back-to-back bookings (one ends at
    11:00, the next starts at 11:00) do not overlap.
    """
    return and_(
        Booking.status == "active",
        Booking.start_time < end,
        Booking.end_time > start,
    )


def _lock_spot(db: Session, spot_id: int) -> None:
    """Stop two requests for the same spot from both passing the overlap check.

    Without this, two requests can both run the check, both see nothing in the
    way, and both insert: a double booking. Writing to the spot row first makes
    the second request wait until the first has committed, so its check sees
    the first booking.
      * SQLite has no row locks; any write takes the database-wide write lock.
      * PostgreSQL/MySQL lock just this spot's row, so other spots aren't blocked
        (the same effect as SELECT ... FOR UPDATE).
    """
    db.execute(
        update(Spot).where(Spot.id == spot_id).values(number=Spot.number),
        execution_options={"synchronize_session": False},
    )


def _resolve_window(start: datetime | None, end: datetime | None) -> tuple[datetime, datetime]:
    """Time window to show availability for; defaults to the next hour."""
    if (start is None) != (end is None):
        raise BadRequestError("Provide both start and end, or neither")
    if start is None:
        start = utc_now()
        return start, start + DEFAULT_WINDOW
    start, end = to_db_time(start), to_db_time(end)
    if end <= start:
        raise BadRequestError("end must be after start")
    return start, end


def _price_for(hourly_price: int, start: datetime, end: datetime) -> int:
    minutes = (end - start).total_seconds() / 60
    return math.ceil(hourly_price * minutes / 60)  # round up to the next rupee


def list_locations(
    db: Session, start: datetime | None = None, end: datetime | None = None
) -> list[LocationOut]:
    start, end = _resolve_window(start, end)

    # Two queries total, however many locations exist (avoids the N+1 query problem).
    locations = db.scalars(
        select(Location).options(selectinload(Location.spots)).order_by(Location.id)
    ).all()
    booked_spot_ids = set(db.scalars(select(Booking.spot_id).where(_overlaps(start, end))).all())

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


def spot_schedule(db: Session, location_id: int, spot_number: str) -> list[SpotBooking]:
    """Active bookings for one spot that haven't finished yet, soonest first."""
    _get_location(db, location_id)
    spot = _get_spot(db, location_id, spot_number)
    bookings = db.scalars(
        select(Booking)
        .where(Booking.spot_id == spot.id, Booking.status == "active", Booking.end_time > utc_now())
        .order_by(Booking.start_time)
    ).all()
    return [
        SpotBooking(booking_id=b.id, start_time=b.start_time, end_time=b.end_time)
        for b in bookings
    ]


def get_stats(db: Session) -> StatsOut:
    now = utc_now()
    location_count = db.scalar(select(func.count(Location.id)))
    total_spots = db.scalar(select(func.count(Spot.id)))
    occupied_now = db.scalar(
        select(func.count(func.distinct(Booking.spot_id))).where(
            Booking.status == "active", Booking.start_time <= now, Booking.end_time > now
        )
    )
    avg_price = db.scalar(select(func.avg(Location.price))) or 0
    return StatsOut(
        locations=location_count,
        total_spots=total_spots,
        available_spots=total_spots - occupied_now,
        booked_spots=occupied_now,
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

    start, end = to_db_time(data.start_time), to_db_time(data.end_time)
    now = utc_now()
    if start < now - PAST_START_GRACE:
        raise BadRequestError("Start time is in the past")
    if start > now + timedelta(days=MAX_DAYS_AHEAD):
        raise BadRequestError(f"Bookings can be made at most {MAX_DAYS_AHEAD} days ahead")

    # Lock first, then check, then insert, all in one transaction.
    _lock_spot(db, spot.id)
    clash = db.scalar(
        select(Booking.id).where(Booking.spot_id == spot.id, _overlaps(start, end)).limit(1)
    )
    if clash is not None:
        db.rollback()  # release the lock straight away
        raise ConflictError("This spot is already booked for part of that time")

    booking = Booking(
        spot_id=spot.id,
        name=data.name,
        vehicle_number=data.vehicle_number,
        start_time=start,
        end_time=end,
        total_price=_price_for(location.price, start, end),
    )
    db.add(booking)
    db.commit()

    return BookingOut(
        message="Spot booked!",
        booking_id=booking.id,
        location=location.name,
        name=booking.name,
        vehicle_number=booking.vehicle_number,
        spot_number=spot.number,
        start_time=booking.start_time,
        end_time=booking.end_time,
        total_price=booking.total_price,
    )


def cancel_booking(db: Session, booking_id: int) -> CancelOut:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise NotFoundError("Booking not found")
    if booking.status == "cancelled":
        raise ConflictError("This booking is already cancelled")
    if booking.end_time <= utc_now():
        raise ConflictError("This booking has already ended")

    # Soft delete: keep the row for history and the activity feed.
    booking.status = "cancelled"
    booking.cancelled_at = utc_now()
    db.commit()

    return CancelOut(
        message="Booking cancelled",
        booking_id=booking.id,
        location=booking.spot.location.name,
        spot_number=booking.spot.number,
    )
