"""Обработчики бота."""

from aiogram import Router

from .common import router as common_router
from .registration import router as registration_router
from .orders import router as orders_router
from .admin import router as admin_router


def setup_routers() -> Router:
    """Настройка всех роутеров."""
    router = Router()
    router.include_router(common_router)
    router.include_router(registration_router)
    router.include_router(orders_router)
    router.include_router(admin_router)
    return router

