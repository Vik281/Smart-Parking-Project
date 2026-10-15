from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from pydantic import AfterValidator, AwareDatetime, BaseModel, Field, field_validator, model_validator

MIN_BOOKING = timedelta(minutes=30)
MAX_BOOKING = timedelta(hours=24)


def _mark_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


# For responses: the database hands back naive UTC times; this labels them as UTC
# so the JSON says "...Z" and the browser converts them to the user's local time.
UtcDatetime = Annotated[datetime, AfterValidator(_mark_utc)]


class LocationOut(BaseModel):
    id: int
    name: str
    address: str
    price: int
    rating: float
    amenities: list[str]
    spot_numbers: list[str]
    booked_spots: list[str]  # spots with a booking overlapping the requested window
    total_spots: int
    spots: int  # spots free for the whole requested window


class BookingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    vehicle_number: str = Field(min_length=1, max_length=20)
    spot_number: str
    # AwareDatetime rejects times without a timezone: "10:00" is ambiguous,
    # "10:00+05:30" is not.
    start_time: AwareDatetime
    end_time: AwareDatetime

    @field_validator("name", "vehicle_number")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("vehicle_number")
    @classmethod
    def normalise_plate(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def check_duration(self) -> "BookingCreate":
        duration = self.end_time - self.start_time
        if duration <= timedelta(0):
            raise ValueError("end_time must be after start_time")
        if duration < MIN_BOOKING:
            raise ValueError("bookings must be at least 30 minutes")
        if duration > MAX_BOOKING:
            raise ValueError("bookings can be at most 24 hours")
        return self


class BookingOut(BaseModel):
    message: str
    booking_id: int
    location: str
    name: str
    vehicle_number: str
    spot_number: str
    start_time: UtcDatetime
    end_time: UtcDatetime
    total_price: int


class SpotBooking(BaseModel):
    """One entry in a spot's schedule. No name or plate: there is no login yet,
    so anyone can see this list."""
    booking_id: int
    start_time: UtcDatetime
    end_time: UtcDatetime


class CancelOut(BaseModel):
    message: str
    booking_id: int
    location: str
    spot_number: str


class StatsOut(BaseModel):
    locations: int
    total_spots: int
    available_spots: int  # free right now
    booked_spots: int  # occupied right now
    avg_price: float


class ActivityItem(BaseModel):
    type: Literal["booked", "cancelled"]
    location: str
    spot_number: str
    at: UtcDatetime
