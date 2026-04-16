from sqlalchemy import Boolean, Column, Integer, Text
from database import Base


class Theme(Base):
    __tablename__ = "themes"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    name            = Column(Text, nullable=False)
    bg_color        = Column(Text, nullable=False)
    card_color      = Column(Text, nullable=False)
    accent_color    = Column(Text, nullable=False)
    accent2_color   = Column(Text, nullable=False)
    accent3_color   = Column(Text, nullable=False)
    text_color      = Column(Text, nullable=False)
    muted_color     = Column(Text, nullable=False)
    border_color    = Column(Text, nullable=False)
    dark_bg_color   = Column(Text, nullable=False)
    dark_card_color = Column(Text, nullable=False)
    is_premium      = Column(Boolean, default=False)
