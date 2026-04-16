# ============================================================
# api/client.py — клиентские эндпоинты (требуют initData)
# ============================================================
# TODO: реализовать в Фазе 2
#   - GET  /clients/me/bookings
#   - POST /bookings
#   - PATCH /bookings/{id}/cancel
#   - PATCH /bookings/{id}/reschedule

from fastapi import APIRouter

router = APIRouter(tags=["Client"])


@router.get("/clients/me/bookings")
async def get_my_bookings():
    # TODO: проверить initData, найти клиента, вернуть записи
    return {"detail": "Будет реализовано в Фазе 2"}


@router.post("/bookings")
async def create_booking():
    # TODO: проверить слот, создать запись, отправить уведомление
    return {"detail": "Будет реализовано в Фазе 2"}
