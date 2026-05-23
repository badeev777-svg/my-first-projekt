from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, JSON, Boolean, ForeignKey, UniqueConstraint, Enum
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=True)
    level = Column(String(3), nullable=False, server_default='A1')
    goal = Column(String(50), nullable=True)
    format = Column(String(10), nullable=False, server_default='text')
    audience = Column(String(10), nullable=False, server_default='adults')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    premium_until = Column(DateTime, nullable=True)

    dialogs = relationship("Dialog", back_populates="user", cascade="all, delete-orphan")
    daily_limits = relationship("DailyLimits", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")


class Dialog(Base):
    __tablename__ = "dialogs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    scenario = Column(String(50), nullable=False)
    level = Column(String(3), nullable=False)
    messages = Column(JSON, nullable=False, server_default='[]')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, server_default='true')

    user = relationship("User", back_populates="dialogs")


class DailyLimits(Base):
    __tablename__ = "daily_limits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    date = Column(Date, nullable=False)
    message_count = Column(Integer, nullable=False, server_default='0')

    user = relationship("User", back_populates="daily_limits")
    __table_args__ = (UniqueConstraint('user_id', 'date', name='uq_user_date'),)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    plan = Column(String(20), nullable=False)
    payment_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="subscriptions")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    amount = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, server_default='RUB')
    status = Column(String(20), nullable=False, server_default='pending')
    method = Column(String(20), nullable=False)
    external_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="payments")
