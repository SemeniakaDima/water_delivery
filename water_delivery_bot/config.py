"""Конфігурація бота для доставки води."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Налаштування застосунку."""
    
    bot_token: str
    admin_ids: list[int]
    
    # Ціна за замовчуванням (для нових клієнтів без індивідуальної ціни)
    default_bottle_price: int = 150  # Ціна за пляшку 19л у гривнях
    
    # Способи оплати
    payment_methods: list[str] = None
    
    def __post_init__(self):
        if self.payment_methods is None:
            self.payment_methods = [
                "💵 Готівкою кур'єру",
                "💳 Карткою кур'єру",
                "🏦 Переказ на картку",
            ]


def load_config() -> Config:
    """Завантаження конфігурації зі змінних оточення."""
    
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN не задано у змінних оточення")
    
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
    
    return Config(
        bot_token=token,
        admin_ids=admin_ids,
        default_bottle_price=int(os.getenv("DEFAULT_BOTTLE_PRICE", 150)),
    )
