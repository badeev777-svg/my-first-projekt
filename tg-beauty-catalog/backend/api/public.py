# ============================================================
# api/public.py — публичные эндпоинты (Mini App клиента)
# ============================================================
# Не требуют авторизации — доступны любому посетителю.
# Все данные изолированы по master slug.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Master, Service, ServicePhoto, PortfolioItem, Review

router = APIRouter(tags=["Public"])


@router.get("/masters/{slug}/profile")
async def get_master_profile(slug: str, db: AsyncSession = Depends(get_db)):
    """Публичный профиль мастера — имя, фото, рейтинг, тема."""
    result = await db.execute(
        select(Master).where(Master.slug == slug, Master.is_active == True)
    )
    master = result.scalar_one_or_none()
    if not master:
        raise HTTPException(404, "Мастер не найден")

    return {
        "id":               master.id,
        "name":             master.name,
        "specialty":        master.specialty,
        "city":             master.city,
        "bio":              master.bio,
        "avatar_url":       master.avatar_url,
        "tags":             master.tags or [],
        "rating":           float(master.rating or 0),
        "reviews_count":    master.reviews_count,
        "rating_breakdown": master.rating_breakdown,
        "accent_color":     master.accent_color,
        "logo_url":         master.logo_url,
    }


@router.get("/masters/{slug}/services")
async def get_master_services(
    slug: str,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Список активных услуг мастера, опционально фильтр по категории."""
    master_result = await db.execute(
        select(Master.id).where(Master.slug == slug, Master.is_active == True)
    )
    master_id = master_result.scalar_one_or_none()
    if not master_id:
        raise HTTPException(404, "Мастер не найден")

    query = select(Service).where(Service.master_id == master_id, Service.is_active == True)
    if category:
        query = query.where(Service.category == category)
    query = query.order_by(Service.sort_order)

    result = await db.execute(query)
    services = result.scalars().all()

    return [
        {
            "id":           s.id,
            "category":     s.category,
            "name":         s.name,
            "description":  s.description,
            "price":        s.price,
            "duration_min": s.duration_min,
            "includes":     s.includes or [],
            "is_popular":   s.is_popular,
        }
        for s in services
    ]


@router.get("/masters/{slug}/portfolio")
async def get_master_portfolio(
    slug: str,
    category: str | None = None,
    limit: int = 30,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Портфолио мастера с фильтром по категории."""
    master_result = await db.execute(
        select(Master.id).where(Master.slug == slug, Master.is_active == True)
    )
    master_id = master_result.scalar_one_or_none()
    if not master_id:
        raise HTTPException(404, "Мастер не найден")

    query = select(PortfolioItem).where(PortfolioItem.master_id == master_id)
    if category:
        query = query.where(PortfolioItem.category == category)
    query = query.order_by(PortfolioItem.sort_order).limit(limit).offset(offset)

    result = await db.execute(query)
    items = result.scalars().all()

    return [
        {
            "id":         i.id,
            "category":   i.category,
            "photo_url":  i.photo_url,
            "label":      i.label,
            "service_id": i.service_id,
        }
        for i in items
    ]


@router.get("/masters/{slug}/reviews")
async def get_master_reviews(
    slug: str,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Отзывы мастера."""
    master_result = await db.execute(
        select(Master).where(Master.slug == slug, Master.is_active == True)
    )
    master = master_result.scalar_one_or_none()
    if not master:
        raise HTTPException(404, "Мастер не найден")

    result = await db.execute(
        select(Review)
        .where(Review.master_id == master.id, Review.is_visible == True)
        .order_by(Review.created_at.desc())
        .limit(limit).offset(offset)
    )
    reviews = result.scalars().all()

    return {
        "rating":           float(master.rating or 0),
        "reviews_count":    master.reviews_count,
        "rating_breakdown": master.rating_breakdown,
        "items": [
            {
                "id":           r.id,
                "rating":       r.rating,
                "text":         r.text,
                "service_name": r.service_name,
                "created_at":   r.created_at.isoformat() if r.created_at else None,
            }
            for r in reviews
        ],
    }
