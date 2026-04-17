# ============================================================
# bot/master_photos.py — загрузка фото через Telegram-бот мастера
# ============================================================
# Команды:
#   /add_photo       — добавить фото к услуге (FSM)
#   /photos <id>     — фото услуги (id из /services)
#   /delete_photo <id> — удалить фото услуги
#   /add_portfolio   — добавить фото в портфолио (FSM)
#   /portfolio       — список позиций портфолио
#   /delete_portfolio <id> — удалить позицию портфолио

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message,
)
from sqlalchemy import select

from database import AsyncSessionLocal
from models.master import Master
from models.portfolio import PortfolioItem
from models.service import Service, ServicePhoto
from services import storage

router = Router()


def _is_master(message: Message, master: Master) -> bool:
    return message.from_user.id == master.telegram_user_id


def _no_r2(obj):
    return obj.answer("R2 не настроен. Добавь переменные окружения R2_* на Render.")


# ============================================================
# FSM: добавление фото к услуге
# ============================================================

class AddServicePhoto(StatesGroup):
    select_service = State()
    waiting_photo  = State()


@router.message(Command("add_photo"))
async def cmd_add_photo(message: Message, master: Master, state: FSMContext):
    if not _is_master(message, master):
        return
    if not storage.is_configured():
        await _no_r2(message)
        return

    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Service)
            .where(Service.master_id == master.id, Service.is_active == True)
            .order_by(Service.sort_order, Service.id)
        )
        services = res.scalars().all()

    if not services:
        await message.answer("Сначала добавь услуги: /add_service")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{s.name} ({s.price}р)", callback_data=f"aphoto:{s.id}")]
        for s in services
    ] + [[InlineKeyboardButton(text="Отмена", callback_data="aphoto:cancel")]])

    await state.set_state(AddServicePhoto.select_service)
    await message.answer("К какой услуге добавить фото?", reply_markup=kb)


@router.callback_query(AddServicePhoto.select_service)
async def on_photo_select_service(cb: CallbackQuery, master: Master, state: FSMContext):
    if cb.data == "aphoto:cancel":
        await state.clear()
        await cb.message.edit_text("Отменено.")
        return

    service_id = int(cb.data.split(":")[1])
    async with AsyncSessionLocal() as db:
        svc = await db.get(Service, service_id)

    if not svc or svc.master_id != master.id:
        await cb.answer("Услуга не найдена.")
        return

    await state.update_data(service_id=service_id, service_name=svc.name)
    await state.set_state(AddServicePhoto.waiting_photo)
    await cb.message.edit_text(f"Услуга: {svc.name}\n\nОтправь фото (не файл, а именно фото).")


@router.message(AddServicePhoto.waiting_photo)
async def on_service_photo_received(message: Message, master: Master, state: FSMContext):
    if not message.photo:
        await message.answer("Нужно именно фото, не файл. Попробуй ещё раз.")
        return

    data = await state.get_data()
    await state.clear()

    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    downloaded = await message.bot.download_file(file.file_path)
    photo_bytes = downloaded.read()

    key = storage.make_key(f"masters/{master.id}/services/{data['service_id']}")
    url = storage.upload_bytes(photo_bytes, key)

    async with AsyncSessionLocal() as db:
        db.add(ServicePhoto(
            service_id=data["service_id"],
            master_id=master.id,
            photo_url=url,
        ))
        await db.commit()

    await message.answer(f"Фото добавлено к услуге «{data['service_name']}».")


# ============================================================
# Просмотр и удаление фото услуги
# ============================================================

@router.message(Command("photos"))
async def cmd_photos(message: Message, master: Master):
    if not _is_master(message, master):
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /photos <id услуги>")
        return

    service_id = int(parts[1])
    async with AsyncSessionLocal() as db:
        svc = await db.get(Service, service_id)
        if not svc or svc.master_id != master.id:
            await message.answer("Услуга не найдена.")
            return

        res = await db.execute(
            select(ServicePhoto)
            .where(ServicePhoto.service_id == service_id)
            .order_by(ServicePhoto.sort_order, ServicePhoto.id)
        )
        photos = res.scalars().all()

    if not photos:
        await message.answer(f"У услуги «{svc.name}» пока нет фото.\n\nДобавить: /add_photo")
        return

    lines = [f"Фото услуги «{svc.name}» ({len(photos)} шт.):"]
    for p in photos:
        lines.append(f"#{p.id} — {p.photo_url}")
    lines.append("\nУдалить: /delete_photo <id фото>")
    await message.answer("\n".join(lines))


@router.message(Command("delete_photo"))
async def cmd_delete_photo(message: Message, master: Master):
    if not _is_master(message, master):
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /delete_photo <id фото>")
        return

    photo_id = int(parts[1])
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(ServicePhoto).where(
                ServicePhoto.id == photo_id,
                ServicePhoto.master_id == master.id,
            )
        )
        photo = res.scalar_one_or_none()
        if not photo:
            await message.answer("Фото не найдено.")
            return

        url = photo.photo_url
        await db.delete(photo)
        await db.commit()

    if storage.is_configured():
        try:
            storage.delete_object(storage.url_to_key(url))
        except Exception:
            pass

    await message.answer(f"Фото #{photo_id} удалено.")


# ============================================================
# FSM: добавление фото в портфолио
# ============================================================

class AddPortfolio(StatesGroup):
    waiting_photo  = State()
    enter_category = State()
    enter_label    = State()


@router.message(Command("add_portfolio"))
async def cmd_add_portfolio(message: Message, master: Master, state: FSMContext):
    if not _is_master(message, master):
        return
    if not storage.is_configured():
        await _no_r2(message)
        return

    await state.set_state(AddPortfolio.waiting_photo)
    await message.answer("Отправь фото для портфолио.")


@router.message(AddPortfolio.waiting_photo)
async def on_portfolio_photo(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("Нужно именно фото. Попробуй ещё раз.")
        return

    photo = message.photo[-1]
    await state.update_data(file_id=photo.file_id)
    await state.set_state(AddPortfolio.enter_category)
    await message.answer("Категория? Например: Маникюр, Педикюр, Ресницы")


@router.message(AddPortfolio.enter_category)
async def on_portfolio_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text.strip())
    await state.set_state(AddPortfolio.enter_label)
    await message.answer("Подпись к фото? (необязательно — отправь \"-\" чтобы пропустить)")


@router.message(AddPortfolio.enter_label)
async def on_portfolio_label(message: Message, master: Master, state: FSMContext):
    label = message.text.strip()
    if label == "-":
        label = None

    data = await state.get_data()
    await state.clear()

    file = await message.bot.get_file(data["file_id"])
    downloaded = await message.bot.download_file(file.file_path)
    photo_bytes = downloaded.read()

    key = storage.make_key(f"masters/{master.id}/portfolio")
    url = storage.upload_bytes(photo_bytes, key)

    async with AsyncSessionLocal() as db:
        db.add(PortfolioItem(
            master_id=master.id,
            category=data["category"],
            photo_url=url,
            label=label,
        ))
        await db.commit()

    await message.answer(
        f"Фото добавлено в портфолио.\n"
        f"Категория: {data['category']}"
        + (f"\nПодпись: {label}" if label else "")
    )


# ============================================================
# Просмотр и удаление портфолио
# ============================================================

@router.message(Command("portfolio"))
async def cmd_portfolio(message: Message, master: Master):
    if not _is_master(message, master):
        return

    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(PortfolioItem)
            .where(PortfolioItem.master_id == master.id)
            .order_by(PortfolioItem.sort_order, PortfolioItem.id)
        )
        items = res.scalars().all()

    if not items:
        await message.answer("Портфолио пустое.\n\nДобавить: /add_portfolio")
        return

    lines = [f"Портфолио ({len(items)} фото):"]
    for item in items:
        label = f" — {item.label}" if item.label else ""
        lines.append(f"#{item.id} [{item.category}]{label}")
    lines.append("\nУдалить: /delete_portfolio <id>")
    await message.answer("\n".join(lines))


@router.message(Command("delete_portfolio"))
async def cmd_delete_portfolio(message: Message, master: Master):
    if not _is_master(message, master):
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /delete_portfolio <id>")
        return

    item_id = int(parts[1])
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(PortfolioItem).where(
                PortfolioItem.id == item_id,
                PortfolioItem.master_id == master.id,
            )
        )
        item = res.scalar_one_or_none()
        if not item:
            await message.answer("Позиция не найдена.")
            return

        url = item.photo_url
        await db.delete(item)
        await db.commit()

    if storage.is_configured():
        try:
            storage.delete_object(storage.url_to_key(url))
        except Exception:
            pass

    await message.answer(f"Позиция #{item_id} удалена из портфолио.")
