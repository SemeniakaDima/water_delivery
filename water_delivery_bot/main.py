"""Главный модуль бота доставки воды."""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config, Config
from database import init_db
from handlers import setup_routers

# Глобальные переменные для доступа из других модулей
bot: Bot = None
config: Config = None


async def main():
    """Точка входа."""
    global bot, config
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("bot.log", encoding="utf-8"),
        ]
    )
    logger = logging.getLogger(__name__)
    
    # Загрузка конфигурации
    try:
        config = load_config()
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        sys.exit(1)
    
    # Инициализация БД
    await init_db()
    logger.info("База данных инициализирована")
    
    # Создание бота и диспетчера
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Middleware для передачи config в обработчики
    @dp.update.outer_middleware()
    async def config_middleware(handler, event, data):
        data["config"] = config
        return await handler(event, data)
    
    # Регистрация роутеров
    router = setup_routers()
    dp.include_router(router)
    
    # Запуск
    logger.info("Бот запускается...")
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

