from sqlalchemy import BigInteger, Boolean, Column, Date, ForeignKey, Integer, Text, Time
from sqlalchemy.orm import relationship
from database import Base


class WorkSchedule(Base):
    __tablename__ = "work_schedule"

    id                = Column(BigInteger, primary_key=True, autoincrement=True)
    master_id         = Column(BigInteger, ForeignKey("masters.id", ondelete="CASCADE"), nullable=False)
    day_of_week       = Column(Integer, nullable=False)   # 0=Пн, 6=Вс
    start_time        = Column(Time, nullable=False)
    end_time          = Column(Time, nullable=False)
    slot_duration_min = Column(Integer, default=90)
    is_working        = Column(Boolean, default=True)

    master = relationship("Master", back_populates="schedule")


class SlotOverride(Base):
    __tablename__ = "slot_overrides"

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    master_id  = Column(BigInteger, ForeignKey("masters.id", ondelete="CASCADE"), nullable=False)
    date       = Column(Date, nullable=False)
    time       = Column(Time)             # NULL = весь день заблокирован
    is_blocked = Column(Boolean, default=True)
    reason     = Column(Text)
