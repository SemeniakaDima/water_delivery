"""Загальні обробники команд."""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import get_user, WATER_TYPE_NAMES, WaterType
from keyboards import main_menu_keyboard
from config import Config

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, config: Config):
    """Обробник команди /start."""
    await state.clear()
    
    user = await get_user(message.from_user.id)
    is_registered = user is not None
    
    welcome_text = (
        "🚰 <b>Ласкаво просимо до сервісу доставки води!</b>\n\n"
        "Ми доставляємо чисту питну воду у пляшках 19 літрів "
        "прямо до ваших дверей.\n\n"
        "🚚 <b>Доставка безкоштовна!</b>\n\n"
    )
    
    if is_registered:
        welcome_text += f"Раді бачити вас знову, <b>{user.full_name}</b>! 👋"
    else:
        welcome_text += (
            "Для оформлення замовлення необхідно пройти реєстрацію.\n"
            "Натисніть кнопку <b>📝 Реєстрація</b> нижче."
        )
    
    await message.answer(
        welcome_text,
        reply_markup=main_menu_keyboard(is_registered),
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обробник команди /help."""
    help_text = (
        "📖 <b>Довідка по боту</b>\n\n"
        "<b>Основні команди:</b>\n"
        "/start - Головне меню\n"
        "/help - Довідка\n"
        "/prices - Ціни\n"
        "/contacts - Контакти\n\n"
        "<b>Як зробити замовлення:</b>\n"
        "1. Зареєструйтесь (ПІБ, телефон, адреса)\n"
        "2. Натисніть «🛒 Зробити замовлення»\n"
        "3. Оберіть тип води\n"
        "4. Оберіть кількість пляшок\n"
        "5. Оберіть спосіб оплати\n"
        "6. Підтвердіть замовлення\n\n"
        "Менеджер зв'яжеться з вами для уточнення часу доставки."
    )
    
    await message.answer(help_text, parse_mode="HTML")


@router.message(F.text == "💰 Ціни")
@router.message(Command("prices"))
async def cmd_prices(message: Message, config: Config):
    """Показати ціни."""
    user = await get_user(message.from_user.id)
    
    # Визначаємо ціну для користувача
    if user and user.custom_price is not None:
        price = user.custom_price
        price_note = "(ваша індивідуальна ціна)"
    else:
        price = config.default_bottle_price
        price_note = ""
    
    prices_text = (
        "💰 <b>Наші ціни</b>\n\n"
        "<b>Асортимент:</b>\n"
    )
    
    for water_type in WaterType:
        prices_text += f"• {WATER_TYPE_NAMES[water_type]}: <b>{price} ₴</b>\n"
    
    prices_text += (
        f"\n{price_note}\n\n"
        "🚚 <b>Доставка: БЕЗКОШТОВНО!</b>\n\n"
        "<b>Приклади розрахунку:</b>\n"
    )
    
    for qty in [1, 2, 3, 5]:
        total = qty * price
        prices_text += f"• {qty} пл. = <b>{total} ₴</b>\n"
    
    await message.answer(prices_text, parse_mode="HTML")


@router.message(F.text == "📞 Контакти")
@router.message(Command("contacts"))
async def cmd_contacts(message: Message):
    """Показати контакти."""
    contacts_text = (
        "📞 <b>Наші контакти</b>\n\n"
        "☎️ Телефон: +38 (068) 811-0-811\n"
        "📱 Viber/Telegram: +38 (068) 811-0-811\n"
        "📧 Email: info@water.kh.ua\n\n"
        "🕐 <b>Час роботи:</b>\n"
        "Пн-Пт: 9:00 - 19:00\n"
        "Сб: 10:00 - 18:00\n"
        "Нд: вихідний\n\n"
        "📍 <b>Зона доставки:</b>\n"
        "Місто та найближчі райони"
    )
    
    await message.answer(contacts_text, parse_mode="HTML")


@router.message(F.text == "❌ Скасувати")
async def cancel_action(message: Message, state: FSMContext):
    """Скасування поточної дії."""
    await state.clear()
    
    user = await get_user(message.from_user.id)
    is_registered = user is not None
    
    await message.answer(
        "Дію скасовано. Ви в головному меню.",
        reply_markup=main_menu_keyboard(is_registered)
    )

