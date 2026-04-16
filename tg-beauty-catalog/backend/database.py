# ============================================================
# database.py — подключение к PostgreSQL через SQLAlchemy
# ============================================================
# Метафора: это «провод» между приложением и базой данных.
# Все запросы к БД идут через этот файл.

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from config import settings

# Движок — это само подключение к базе данных.
# echo=True в режиме разработки выводит все SQL-запросы в консоль (удобно для отладки).
#
# NullPool — не кешируем соединения на нашей стороне.
# Supabase уже использует PgBouncer (transaction pooling), поэтому
# двойной пул только мешает: соединения закрываются на стороне PgBouncer,
# а SQLAlchemy держит «мёртвые» соединения в своём пуле.
engine = create_async_engine(
    settings.database_url,
    echo=settings.is_dev,
    poolclass=NullPool,
)

# Фабрика сессий — каждый HTTP-запрос получает свою сессию (как отдельный разговор с БД).
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Базовый класс для всех ORM-моделей
class Base(DeclarativeBase):
    pass


# Dependency для FastAPI — передаёт сессию в каждый endpoint
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
