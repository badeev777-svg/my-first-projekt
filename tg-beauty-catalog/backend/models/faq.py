from sqlalchemy import BigInteger, Column, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from database import Base


class FaqItem(Base):
    __tablename__ = "faq_items"

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    master_id  = Column(BigInteger, ForeignKey("masters.id", ondelete="CASCADE"), nullable=False)
    question   = Column(Text, nullable=False)
    answer     = Column(Text, nullable=False)
    sort_order = Column(Integer, default=0)

    master = relationship("Master", back_populates="faq_items")
