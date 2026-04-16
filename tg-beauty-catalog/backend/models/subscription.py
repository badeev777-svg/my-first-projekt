from sqlalchemy import BigInteger, Column, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.sql import func
from database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id                         = Column(BigInteger, primary_key=True, autoincrement=True)
    master_id                  = Column(BigInteger, ForeignKey("masters.id"), nullable=False)
    telegram_payment_charge_id = Column(Text, unique=True, nullable=False)
    stars_amount               = Column(Integer, nullable=False)
    period_months              = Column(Integer, default=1)
    starts_at                  = Column(TIMESTAMP(timezone=True), nullable=False)
    expires_at                 = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at                 = Column(TIMESTAMP(timezone=True), server_default=func.now())
