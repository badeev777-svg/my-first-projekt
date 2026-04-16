from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Integer, Numeric, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Master(Base):
    __tablename__ = "masters"

    id                      = Column(BigInteger, primary_key=True, autoincrement=True)
    telegram_user_id        = Column(BigInteger, unique=True, nullable=False)
    bot_token               = Column(Text, nullable=False)        # хранится зашифрованным (Fernet)
    bot_token_hash          = Column(Text, unique=True, nullable=False)
    bot_username            = Column(Text, nullable=False)
    slug                    = Column(Text, unique=True, nullable=False)

    # Профиль
    name                    = Column(Text, nullable=False)
    specialty               = Column(Text)
    city                    = Column(Text)
    bio                     = Column(Text)
    avatar_url              = Column(Text)
    tags                    = Column(ARRAY(Text))

    # Рейтинг (пересчитывается триггером при добавлении отзыва)
    rating                  = Column(Numeric(2, 1), default=0)
    reviews_count           = Column(Integer, default=0)
    rating_breakdown        = Column(JSONB, default={"5": 0, "4": 0, "3": 0, "2": 0, "1": 0})

    # Подписка
    subscription_status     = Column(Text, default="free")
    subscription_expires_at = Column(TIMESTAMP(timezone=True))
    services_limit          = Column(Integer, default=5)

    # Тема оформления
    theme_id                = Column(Integer, ForeignKey("themes.id"), default=1)
    accent_color            = Column(Text)
    logo_url                = Column(Text)

    # Статус
    is_active               = Column(Boolean, default=True)
    webhook_set_at          = Column(TIMESTAMP(timezone=True))
    created_at              = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at              = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Связи
    theme        = relationship("Theme")
    services     = relationship("Service", back_populates="master", cascade="all, delete-orphan")
    portfolio    = relationship("PortfolioItem", back_populates="master", cascade="all, delete-orphan")
    clients      = relationship("Client", back_populates="master", cascade="all, delete-orphan")
    schedule     = relationship("WorkSchedule", back_populates="master", cascade="all, delete-orphan")
    faq_items    = relationship("FaqItem", back_populates="master", cascade="all, delete-orphan")
    settings_rel = relationship("MasterSettings", back_populates="master", uselist=False, cascade="all, delete-orphan")


class MasterSettings(Base):
    __tablename__ = "master_settings"

    master_id                   = Column(BigInteger, ForeignKey("masters.id", ondelete="CASCADE"), primary_key=True)
    cancellation_hours          = Column(Integer, default=24)
    reminder_24h_enabled        = Column(Boolean, default=True)
    reminder_2h_enabled         = Column(Boolean, default=True)
    welcome_message             = Column(Text, default="Добро пожаловать! Я помогу вам записаться.")
    booking_confirm_message     = Column(Text, default="Ваша запись подтверждена! Ждём вас.")
    days_advance_booking        = Column(Integer, default=30)
    forward_unknown_to_master   = Column(Boolean, default=True)

    master = relationship("Master", back_populates="settings_rel")
