from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


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
        # At most one *active* booking per spot, enforced by the database itself.
        # This is what actually prevents double booking when two requests race.
        Index(
            "uq_one_active_booking_per_spot",
            "spot_id",
            unique=True,
            sqlite_where=text("status = 'active'"),
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    spot_id: Mapped[int] = mapped_column(ForeignKey("spots.id"))
    name: Mapped[str] = mapped_column(String(60))
    vehicle_number: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | cancelled
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    cancelled_at: Mapped[datetime | None] = mapped_column(default=None)

    spot: Mapped[Spot] = relationship(back_populates="bookings")
