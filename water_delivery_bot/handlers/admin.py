"""Обробники для адміністраторів."""

import logging
import random
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import (
    get_all_pending_orders,
    update_order_status,
    get_order_with_user,
    get_all_users,
    get_user,
    set_user_price,
    OrderStatus,
    WATER_TYPE_NAMES
)
from keyboards import admin_order_keyboard, users_list_keyboard, admin_menu_keyboard, order_complete_keyboard
from states import AdminStates
from config import Config

router = Router()
logger = logging.getLogger(__name__)

# Веселі повідомлення для статусу "У доставці"
DELIVERY_MESSAGES = [
    "🚗 <b>Ваше замовлення #{order_id} вже мчить до вас!</b>\n\n"
    "Наш кур'єр вже в дорозі та скоро буде! Готуйте склянки! 🥤",
    
    "🏃‍♂️ <b>Замовлення #{order_id} на шляху!</b>\n\n"
    "Вода вже їде до вас! Кур'єр поспішає, щоб ви насолодились свіжою водою! 💧",
    
    "🚀 <b>Замовлення #{order_id} відправлено!</b>\n\n"
    "Наш супер-кур'єр вже несе вам живильну воду! Очікуйте дзвінок! 📞",
    
    "🎉 <b>Чудові новини! Замовлення #{order_id} в дорозі!</b>\n\n"
    "Чиста вода Ефект вже прямує до вас! Скоро будемо! 🌊",
    
    "💨 <b>Замовлення #{order_id} летить до вас!</b>\n\n"
    "Кур'єр вже вирушив! Залишилось зовсім трохи до зустрічі! 😊",
    
    "🌟 <b>Замовлення #{order_id} вже в дорозі!</b>\n\n"
    "Наш чарівний кур'єр везе вам найкращу воду! Чекайте на дзвінок! ✨",
    
    "🏎️ <b>Вжух! Замовлення #{order_id} мчить до вас!</b>\n\n"
    "Тримайтесь! Свіжа вода вже на підході! 💪",
    
    "📦 <b>Замовлення #{order_id} передано кур'єру!</b>\n\n"
    "Ваша вода вже подорожує до вас! Скоро зустрінемось! 🤝",
]

# Теплі слова для підтвердження
CONFIRM_MESSAGES = [
    "✅ <b>Замовлення #{order_id} підтверджено!</b>\n\n"
    "Дякуємо за ваше замовлення! Ми вже готуємо його до відправки. "
    "Незабаром кур'єр вирушить до вас! 💙",
    
    "✅ <b>Ваше замовлення #{order_id} прийнято!</b>\n\n"
    "Чудовий вибір! Ми цінуємо вашу довіру. "
    "Замовлення готується до доставки! 🌟",
    
    "✅ <b>Замовлення #{order_id} в обробці!</b>\n\n"
    "Дякуємо, що обираєте нас! Ваше замовлення вже обробляється, "
    "скоро воно буде в дорозі! 💧",
]


def is_admin(user_id: int, config: Config) -> bool:
    """Перевірка, чи є користувач адміністратором."""
    return user_id in config.admin_ids


def format_time_diff(created_at: datetime, action_at: datetime) -> str:
    """Форматування різниці в часі."""
    diff = action_at - created_at
    total_seconds = int(diff.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds} сек"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes} хв"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours} год {minutes} хв"


# ============= ГОЛОВНЕ МЕНЮ АДМІНА =============

@router.message(Command("admin"))
async def admin_panel(message: Message, config: Config):
    """Панель адміністратора."""
    if not is_admin(message.from_user.id, config):
        await message.answer("❌ У вас немає доступу до цієї команди.")
        return
    
    await message.answer(
        "🔧 <b>Панель адміністратора</b>\n\n"
        "Оберіть дію:",
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_menu_back")
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext, config: Config):
    """Повернення до головного меню адміна."""
    if not is_admin(callback.from_user.id, config):
        await callback.answer("❌ Немає доступу", show_alert=True)
        return
    
    await state.clear()
    await callback.message.edit_text(
        "🔧 <b>Панель адміністратора</b>\n\n"
        "Оберіть дію:",
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML"
    )


# ============= ЗАМОВЛЕННЯ =============

@router.callback_query(F.data == "admin_menu_orders")
async def admin_orders(callback: CallbackQuery, config: Config):
    """Перегляд замовлень."""
    if not is_admin(callback.from_user.id, config):
        await callback.answer("❌ Немає доступу", show_alert=True)
        return
    
    orders = await get_all_pending_orders()
    
    if not orders:
        await callback.message.edit_text(
            "📋 <b>Замовлення</b>\n\n"
            "Немає активних замовлень.",
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await callback.message.edit_text(
        f"📋 <b>Активні замовлення: {len(orders)}</b>",
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML"
    )
    
    status_icons = {
        OrderStatus.PENDING: "⏳ Очікує",
        OrderStatus.CONFIRMED: "✅ Підтверджено",
        OrderStatus.DELIVERING: "🚗 У доставці",
    }
    
    for order, user in orders:
        water_name = WATER_TYPE_NAMES.get(order.water_type, "Вода")
        status_text = status_icons.get(order.status, str(order.status.value))
        
        # Час підтвердження
        time_info = ""
        if order.confirmed_at:
            time_diff = format_time_diff(order.created_at, order.confirmed_at)
            time_info = f"\n⏱️ Підтверджено за: {time_diff}"
        
        await callback.message.answer(
            f"<b>Замовлення #{order.id}</b> {status_text}\n\n"
            f"👤 {user.full_name}\n"
            f"📱 {user.phone}\n"
            f"📍 {user.address}\n\n"
            f"💧 {water_name}\n"
            f"📦 {order.quantity} пл.\n"
            f"💵 {order.total_price} ₴\n"
            f"💳 {order.payment_method}\n"
            f"💬 {order.comment or 'без коментаря'}\n"
            f"📅 {order.created_at.strftime('%d.%m.%Y %H:%M')}"
            f"{time_info}",
            reply_markup=admin_order_keyboard(order.id, order.status),
            parse_mode="HTML"
        )


# ============= ЦІНИ КЛІЄНТІВ =============

@router.message(Command("prices"))
async def admin_prices_command(message: Message, config: Config):
    """Управління цінами користувачів (команда)."""
    if not is_admin(message.from_user.id, config):
        await message.answer("❌ У вас немає доступу до цієї команди.")
        return
    
    await show_prices_list(message, config)


@router.callback_query(F.data == "admin_menu_prices")
async def admin_prices(callback: CallbackQuery, config: Config):
    """Управління цінами користувачів."""
    if not is_admin(callback.from_user.id, config):
        await callback.answer("❌ Немає доступу", show_alert=True)
        return
    
    await show_prices_list(callback.message, config, edit=True)


async def show_prices_list(message: Message, config: Config, edit: bool = False):
    """Показати список користувачів для встановлення цін."""
    users = await get_all_users()
    
    if not users:
        text = "👥 <b>Ціни клієнтів</b>\n\nНемає зареєстрованих користувачів."
        if edit:
            await message.edit_text(text, reply_markup=admin_menu_keyboard(), parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=admin_menu_keyboard(), parse_mode="HTML")
        return
    
    text = (
        f"💰 <b>Ціни клієнтів ({len(users)})</b>\n\n"
        f"Ціна за замовчуванням: <b>{config.default_bottle_price} ₴</b>\n\n"
        "Оберіть клієнта для встановлення індивідуальної ціни:"
    )
    
    if edit:
        await message.edit_text(text, reply_markup=users_list_keyboard(users), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=users_list_keyboard(users), parse_mode="HTML")


# ============= ВСІ КЛІЄНТИ =============

@router.callback_query(F.data == "admin_menu_clients")
async def admin_clients(callback: CallbackQuery, config: Config):
    """Перегляд всіх клієнтів."""
    if not is_admin(callback.from_user.id, config):
        await callback.answer("❌ Немає доступу", show_alert=True)
        return
    
    users = await get_all_users()
    
    if not users:
        await callback.message.edit_text(
            "👥 <b>Клієнти</b>\n\nНемає зареєстрованих клієнтів.",
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    clients_text = f"👥 <b>Клієнти ({len(users)})</b>\n\n"
    
    for user in users:
        price_text = f"{user.custom_price} ₴" if user.custom_price else f"{config.default_bottle_price} ₴ (станд.)"
        clients_text += (
            f"👤 <b>{user.full_name}</b>\n"
            f"📱 {user.phone}\n"
            f"📍 {user.address}\n"
            f"💰 Ціна: {price_text}\n"
            f"───────────────\n"
        )
    
    if len(clients_text) > 4000:
        clients_text = clients_text[:3900] + "\n\n... (показано перших клієнтів)"
    
    await callback.message.edit_text(
        clients_text,
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML"
    )


# ============= НАВІГАЦІЯ ПО КОРИСТУВАЧАХ =============

@router.callback_query(F.data.startswith("users_page_"))
async def handle_users_page(callback: CallbackQuery, config: Config):
    """Навігація по сторінках користувачів."""
    if not is_admin(callback.from_user.id, config):
        await callback.answer("❌ Немає доступу", show_alert=True)
        return
    
    page = int(callback.data.split("_")[2])
    users = await get_all_users()
    
    await callback.message.edit_reply_markup(
        reply_markup=users_list_keyboard(users, page)
    )


@router.callback_query(F.data.startswith("setprice_user_"))
async def handle_select_user_for_price(callback: CallbackQuery, state: FSMContext, config: Config):
    """Вибір користувача для встановлення ціни."""
    if not is_admin(callback.from_user.id, config):
        await callback.answer("❌ Немає доступу", show_alert=True)
        return
    
    telegram_id = int(callback.data.split("_")[2])
    user = await get_user(telegram_id)
    
    if not user:
        await callback.answer("❌ Користувача не знайдено", show_alert=True)
        return
    
    current_price = user.custom_price if user.custom_price else config.default_bottle_price
    price_type = "індивідуальна" if user.custom_price else "за замовчуванням"
    
    await state.update_data(price_user_telegram_id=telegram_id)
    await state.set_state(AdminStates.waiting_for_price)
    
    await callback.message.edit_text(
        f"👤 <b>{user.full_name}</b>\n"
        f"📱 {user.phone}\n\n"
        f"💰 Поточна ціна: <b>{current_price} ₴</b> ({price_type})\n\n"
        "Введіть нову ціну за пляшку (число в гривнях)\n"
        "або напишіть <b>0</b> щоб скинути до ціни за замовчуванням:",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_for_price)
async def process_new_price(message: Message, state: FSMContext, config: Config):
    """Обробка нової ціни."""
    if not is_admin(message.from_user.id, config):
        await state.clear()
        return
    
    try:
        price = int(message.text.strip())
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введіть коректне число (0 або більше):")
        return
    
    data = await state.get_data()
    telegram_id = data.get("price_user_telegram_id")
    
    if not telegram_id:
        await state.clear()
        await message.answer("❌ Помилка. Спробуйте ще раз /admin")
        return
    
    user = await get_user(telegram_id)
    
    if price == 0:
        await set_user_price(telegram_id, None)
        await message.answer(
            f"✅ Ціну для <b>{user.full_name}</b> скинуто до стандартної "
            f"(<b>{config.default_bottle_price} ₴</b>)\n\n"
            "Повернутися до меню: /admin",
            parse_mode="HTML"
        )
    else:
        await set_user_price(telegram_id, price)
        await message.answer(
            f"✅ Встановлено індивідуальну ціну для <b>{user.full_name}</b>: "
            f"<b>{price} ₴</b> за пляшку\n\n"
            "Повернутися до меню: /admin",
            parse_mode="HTML"
        )
    
    await state.clear()


# ============= ЗАКРИТТЯ МЕНЮ =============

@router.callback_query(F.data == "close_admin")
async def close_admin_panel(callback: CallbackQuery, state: FSMContext):
    """Закрити адмін-панель."""
    await state.clear()
    await callback.message.delete()


# ============= ОБРОБКА ДІЙ З ЗАМОВЛЕННЯМИ =============

@router.callback_query(F.data.regexp(r"^admin_(confirm|deliver|complete|cancel)_\d+$"))
async def handle_admin_action(callback: CallbackQuery, config: Config):
    """Обробка дій адміністратора з замовленнями."""
    if not is_admin(callback.from_user.id, config):
        await callback.answer("❌ Немає доступу", show_alert=True)
        return
    
    parts = callback.data.split("_")
    action = parts[1]
    order_id = int(parts[2])
    
    status_map = {
        "confirm": OrderStatus.CONFIRMED,
        "deliver": OrderStatus.DELIVERING,
        "complete": OrderStatus.COMPLETED,
        "cancel": OrderStatus.CANCELLED,
    }
    
    status_names = {
        "confirm": "✅ Підтверджено",
        "deliver": "🚗 У доставці",
        "complete": "✔️ Виконано",
        "cancel": "❌ Скасовано",
    }
    
    if action not in status_map:
        return
    
    # Отримуємо дані про замовлення та користувача
    order_data = await get_order_with_user(order_id)
    
    if not order_data:
        await callback.answer("❌ Замовлення не знайдено", show_alert=True)
        return
    
    order, user = order_data
    
    # Оновлюємо статус
    await update_order_status(order_id, status_map[action])
    
    # Час від створення до підтвердження
    time_info = ""
    if action == "confirm":
        time_diff = format_time_diff(order.created_at, datetime.now())
        time_info = f"\n⏱️ Підтверджено за: {time_diff}"
    
    # Оновлюємо повідомлення адміна
    current_text = callback.message.text or callback.message.caption
    new_text = current_text + f"\n\n<b>Статус: {status_names[action]}</b>{time_info}"
    
    # Видаляємо кнопки для завершених/скасованих
    new_keyboard = None
    if action in ["confirm", "deliver"]:
        new_keyboard = admin_order_keyboard(order_id, status_map[action])
    
    await callback.message.edit_text(
        new_text,
        reply_markup=new_keyboard,
        parse_mode="HTML"
    )
    
    await callback.answer(f"Замовлення #{order_id}: {status_names[action]}")
    
    # Сповіщення користувача
    bot = callback.bot
    try:
        if action == "confirm":
            # Теплі слова підтвердження
            user_message = random.choice(CONFIRM_MESSAGES).format(order_id=order_id)
            await bot.send_message(
                chat_id=user.telegram_id,
                text=user_message,
                parse_mode="HTML"
            )
        
        elif action == "deliver":
            # Веселе повідомлення про доставку + кнопка "Отримано"
            user_message = random.choice(DELIVERY_MESSAGES).format(order_id=order_id)
            await bot.send_message(
                chat_id=user.telegram_id,
                text=user_message,
                reply_markup=order_complete_keyboard(order_id),
                parse_mode="HTML"
            )
        
        elif action == "complete":
            await bot.send_message(
                chat_id=user.telegram_id,
                text=f"✔️ <b>Замовлення #{order_id} виконано!</b>\n\n"
                     "Дякуємо за замовлення! Будемо раді бачити вас знову 💙",
                parse_mode="HTML"
            )
        
        elif action == "cancel":
            await bot.send_message(
                chat_id=user.telegram_id,
                text=f"❌ <b>Замовлення #{order_id} скасовано</b>\n\n"
                     "На жаль, ваше замовлення було скасовано. "
                     "Якщо у вас є питання, зв'яжіться з нами.",
                parse_mode="HTML"
            )
        
        logger.info(f"Сповіщення про статус замовлення #{order_id} надіслано користувачу {user.telegram_id}")
    except Exception as e:
        logger.error(f"Помилка відправки сповіщення користувачу {user.telegram_id}: {e}")
