from sqlalchemy import BigInteger, Boolean, Column, Date, ForeignKey, Integer, Text, Time, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id            = Column(BigInteger, primary_key=True, autoincrement=True)
    master_id     = Column(BigInteger, ForeignKey("masters.id"), nullable=False)
    client_id     = Column(BigInteger, ForeignKey("clients.id"), nullable=False)
    service_id    = Column(BigInteger, ForeignKey("services.id", ondelete="SET NULL"))

    # Снимок услуги на момент записи
    service_name  = Column(Text, nullable=False)
    service_price = Column(Integer, nullable=False)
    duration_min  = Column(Integer, nullable=False)

    date          = Column(Date, nullable=False)
    time          = Column(Time, nullable=False)
    phone         = Column(Text, nullable=False)
    comment       = Column(Text)

    status        = Column(Text, default="confirmed")
    cancelled_by  = Column(Text)
    cancelled_at  = Column(TIMESTAMP(timezone=True))

    reminder_24h_sent = Column(Boolean, default=False)
    reminder_2h_sent  = Column(Boolean, default=False)

    created_at    = Column(TIMESTAMP(timezone=True), server_default=func.now())

    client  = relationship("Client", back_populates="bookings")
    reviews = relationship("Review", back_populates="booking")
