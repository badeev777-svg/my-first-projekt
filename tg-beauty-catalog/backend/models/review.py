from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Review(Base):
    __tablename__ = "reviews"

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    master_id    = Column(BigInteger, ForeignKey("masters.id", ondelete="CASCADE"), nullable=False)
    client_id    = Column(BigInteger, ForeignKey("clients.id", ondelete="SET NULL"))
    booking_id   = Column(BigInteger, ForeignKey("bookings.id", ondelete="SET NULL"))
    rating       = Column(Integer, nullable=False)
    text         = Column(Text)
    service_name = Column(Text)
    is_visible   = Column(Boolean, default=True)
    created_at   = Column(TIMESTAMP(timezone=True), server_default=func.now())

    booking = relationship("Booking", back_populates="reviews")
