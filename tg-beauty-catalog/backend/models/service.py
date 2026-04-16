from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Service(Base):
    __tablename__ = "services"

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    master_id    = Column(BigInteger, ForeignKey("masters.id", ondelete="CASCADE"), nullable=False)
    category     = Column(Text, nullable=False)
    name         = Column(Text, nullable=False)
    description  = Column(Text)
    price        = Column(Integer, nullable=False)
    duration_min = Column(Integer, nullable=False)
    includes     = Column(JSONB)
    is_popular   = Column(Boolean, default=False)
    sort_order   = Column(Integer, default=0)
    is_active    = Column(Boolean, default=True)
    created_at   = Column(TIMESTAMP(timezone=True), server_default=func.now())

    master = relationship("Master", back_populates="services")
    photos = relationship("ServicePhoto", back_populates="service", cascade="all, delete-orphan")


class ServicePhoto(Base):
    __tablename__ = "service_photos"

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    service_id = Column(BigInteger, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    master_id  = Column(BigInteger, ForeignKey("masters.id", ondelete="CASCADE"), nullable=False)
    photo_url  = Column(Text, nullable=False)
    sort_order = Column(Integer, default=0)

    service = relationship("Service", back_populates="photos")
