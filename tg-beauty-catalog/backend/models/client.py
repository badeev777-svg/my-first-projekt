from sqlalchemy import BigInteger, Column, Date, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Client(Base):
    __tablename__ = "clients"

    id                = Column(BigInteger, primary_key=True, autoincrement=True)
    master_id         = Column(BigInteger, ForeignKey("masters.id", ondelete="CASCADE"), nullable=False)
    telegram_user_id  = Column(BigInteger, nullable=False)
    telegram_chat_id  = Column(BigInteger, nullable=False)
    first_name        = Column(Text)
    last_name         = Column(Text)
    username          = Column(Text)
    phone             = Column(Text)
    master_notes      = Column(Text)      # приватные заметки мастера
    visits_count      = Column(Integer, default=0)
    last_visit_at     = Column(Date)
    created_at        = Column(TIMESTAMP(timezone=True), server_default=func.now())

    master   = relationship("Master", back_populates="clients")
    bookings = relationship("Booking", back_populates="client")
