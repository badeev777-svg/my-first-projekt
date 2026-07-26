from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from sqlalchemy import String, Text, Integer, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DB_PATH = Path(__file__).parent.parent / "data" / "leads.db"
DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DB_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Source(str, Enum):
    telegram = "telegram"
    fl = "fl"
    freelance_ru = "freelance_ru"
    habr = "habr"
    kwork = "kwork"
    profi = "profi"
    vk = "vk"


class Status(str, Enum):
    new = "new"
    viewed = "viewed"
    archived = "archived"


class DealStage(str, Enum):
    lead = "lead"
    negotiation = "negotiation"
    won = "won"
    lost = "lost"


class Base(DeclarativeBase):
    pass


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(SAEnum(Source), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(512))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    budget: Mapped[int | None] = mapped_column(Integer)
    contact: Mapped[str | None] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(SAEnum(Status), default=Status.new, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    tags: Mapped[str | None] = mapped_column(String(512))
    summary: Mapped[str | None] = mapped_column(Text)
    relevance_score: Mapped[int | None] = mapped_column(Integer)
    estimated_budget: Mapped[int | None] = mapped_column(Integer)
    processed: Mapped[bool] = mapped_column(default=False, nullable=False)

    assigned_to: Mapped[str | None] = mapped_column(String(128))
    deal_stage: Mapped[str] = mapped_column(SAEnum(DealStage), default=DealStage.lead, nullable=False)
    deal_value: Mapped[int | None] = mapped_column(Integer)


class LeadAction(Base):
    __tablename__ = "lead_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(256))
    new_value: Mapped[str] = mapped_column(String(256), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(128), default="admin", nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512))


class DemoUser(Base):
    __tablename__ = "demo_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip_address: Mapped[str] = mapped_column(String(45), unique=True, nullable=False)
    used_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


async def init_db(demo: bool = False) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if demo:
        await _load_demo_data()


async def _load_demo_data() -> None:
    from datetime import timedelta

    demo_leads = [
        {
            "source": "telegram",
            "source_url": "https://t.me/freelance_ru/12345",
            "title": "Нужен сайт для интернет-магазина",
            "text": "Требуется разработка современного интернет-магазина на базе WooCommerce. Бюджет 150 тыс рублей. Сроки 2 месяца.",
            "budget": 150000,
            "contact": "@developer123",
            "created_at": datetime.now(timezone.utc) - timedelta(days=2),
            "status": Status.viewed,
            "relevance_score": 95,
            "tags": "fullstack,backend,frontend",
            "summary": "E-commerce разработка на WooCommerce с интеграциями и оптимизацией.",
            "estimated_budget": 140000,
            "processed": True,
            "assigned_to": "admin",
            "deal_stage": DealStage.negotiation,
            "deal_value": 140000,
        },
        {
            "source": "fl",
            "source_url": "https://www.fl.ru/projects/67890",
            "title": "Создание лендинга для стоматологии",
            "text": "Нужен одностраничный сайт для стоматологической клиники. Адаптивный дизайн, интеграция с CRM. Бюджет 80 тыс руб.",
            "budget": 80000,
            "contact": None,
            "created_at": datetime.now(timezone.utc) - timedelta(days=1),
            "status": Status.new,
            "relevance_score": 88,
            "tags": "frontend,design",
            "summary": "Лендинг с адаптивным дизайном и CRM интеграцией для стоматологии.",
            "estimated_budget": 75000,
            "processed": True,
            "assigned_to": "ivan",
            "deal_stage": DealStage.lead,
            "deal_value": None,
        },
        {
            "source": "habr",
            "source_url": "https://freelance.habr.com/tasks/11111",
            "title": "SEO-продвижение сайта",
            "text": "Комплексное SEO-продвижение интернет-магазина электроники. Анализ конкурентов, оптимизация контента. Бюджет 50 тыс руб/мес.",
            "budget": 50000,
            "contact": None,
            "created_at": datetime.now(timezone.utc) - timedelta(hours=12),
            "status": Status.new,
            "relevance_score": 72,
            "tags": "seo,marketing",
            "summary": "SEO оптимизация и продвижение для e-commerce проекта.",
            "estimated_budget": 55000,
            "processed": True,
            "assigned_to": None,
            "deal_stage": DealStage.lead,
            "deal_value": None,
        },
        {
            "source": "telegram",
            "source_url": "https://t.me/web_zakazy/54321",
            "title": "Верстка PSD макета",
            "text": "Требуется верстка PSD макета в HTML/CSS. Pixel perfect, адаптивность. Бюджет 25 тыс рублей.",
            "budget": 25000,
            "contact": "@designer456",
            "created_at": datetime.now(timezone.utc) - timedelta(hours=6),
            "status": Status.new,
            "relevance_score": 85,
            "tags": "frontend,design",
            "summary": "Верстка PSD макета в HTML/CSS с адаптивностью и кроссбраузерностью.",
            "estimated_budget": 22000,
            "processed": True,
            "assigned_to": "maria",
            "deal_stage": DealStage.won,
            "deal_value": 20000,
        },
        {
            "source": "fl",
            "source_url": "https://www.fl.ru/projects/99999",
            "title": "Разработка корпоративного сайта",
            "text": "Создание корпоративного сайта для IT-компании. 5 страниц, блог, контакты. Бюджет 120 тыс руб.",
            "budget": 120000,
            "contact": None,
            "created_at": datetime.now(timezone.utc) - timedelta(days=3),
            "status": Status.archived,
            "relevance_score": 92,
            "tags": "fullstack,frontend",
            "summary": "Корпоративный сайт с блогом и системой управления контентом.",
            "estimated_budget": 115000,
            "processed": True,
            "assigned_to": "admin",
            "deal_stage": DealStage.lost,
            "deal_value": None,
        },
    ]

    async with SessionLocal() as session:
        for data in demo_leads:
            lead = Lead(
                source=data["source"],
                source_url=data["source_url"],
                title=data["title"],
                text=data["text"],
                budget=data["budget"],
                contact=data["contact"],
                created_at=data["created_at"],
                fetched_at=data["created_at"],
                status=data["status"],
                relevance_score=data.get("relevance_score"),
                tags=data.get("tags"),
                summary=data.get("summary"),
                estimated_budget=data.get("estimated_budget"),
                processed=data.get("processed", False),
                assigned_to=data.get("assigned_to"),
                deal_stage=data.get("deal_stage", DealStage.lead),
                deal_value=data.get("deal_value"),
            )
            session.add(lead)
        await session.commit()


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
