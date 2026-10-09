from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LocationOut(BaseModel):
    id: int
    name: str
    address: str
    price: int
    rating: float
    amenities: list[str]
    spot_numbers: list[str]
    booked_spots: list[str]
    total_spots: int
    spots: int  # available spots


class BookingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    vehicle_number: str = Field(min_length=1, max_length=20)
    spot_number: str

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


class BookingOut(BaseModel):
    message: str
    booking_id: int
    location: str
    name: str
    vehicle_number: str
    spot_number: str
    available_spots: int


class CancelOut(BaseModel):
    message: str
    location: str
    spot_number: str
    available_spots: int


class StatsOut(BaseModel):
    locations: int
    total_spots: int
    available_spots: int
    booked_spots: int
    avg_price: float


class ActivityItem(BaseModel):
    type: Literal["booked", "cancelled"]
    location: str
    spot_number: str
    at: datetime
