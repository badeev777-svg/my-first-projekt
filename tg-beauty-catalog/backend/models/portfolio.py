from sqlalchemy import BigInteger, Column, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    master_id  = Column(BigInteger, ForeignKey("masters.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(BigInteger, ForeignKey("services.id", ondelete="SET NULL"))
    category   = Column(Text, nullable=False)
    photo_url  = Column(Text, nullable=False)
    label      = Column(Text)
    sort_order = Column(Integer, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    master = relationship("Master", back_populates="portfolio")
