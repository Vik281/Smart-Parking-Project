from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.timeutils import utc_now


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(200))
    price: Mapped[int]  # rupees per hour
    rating: Mapped[float]
    amenities: Mapped[list[str]] = mapped_column(JSON, default=list)

    spots: Mapped[list["Spot"]] = relationship(
        back_populates="location", order_by="Spot.id", cascade="all, delete-orphan"
    )


class Spot(Base):
    __tablename__ = "spots"
    __table_args__ = (UniqueConstraint("location_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    number: Mapped[str] = mapped_column(String(20))  # e.g. "CM-3"

    location: Mapped[Location] = relationship(back_populates="spots")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="spot")


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        # The database refuses a booking that ends before it starts, even if a bug
        # in the application lets one through.
        CheckConstraint("end_time > start_time", name="ck_booking_ends_after_start"),
        # The overlap check filters by spot and time on every booking, so index it.
        Index("ix_bookings_spot_time", "spot_id", "start_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    spot_id: Mapped[int] = mapped_column(ForeignKey("spots.id"))
    name: Mapped[str] = mapped_column(String(60))
    vehicle_number: Mapped[str] = mapped_column(String(20))
    # Half-open interval [start_time, end_time): a booking ending at 11:00 does
    # not clash with one starting at 11:00. Stored as naive UTC (see timeutils).
    start_time: Mapped[datetime]
    end_time: Mapped[datetime]
    # Price is copied at booking time, so changing a location's hourly rate
    # later never changes what an existing customer owes.
    total_price: Mapped[int]
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | cancelled
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    cancelled_at: Mapped[datetime | None] = mapped_column(default=None)

    spot: Mapped[Spot] = relationship(back_populates="bookings")
