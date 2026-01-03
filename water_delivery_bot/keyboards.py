"""Клавіатури бота."""

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from config import Config
from database import WaterType, WATER_TYPE_NAMES, User, OrderStatus


def main_menu_keyboard(is_registered: bool = False) -> ReplyKeyboardMarkup:
    """Головне меню."""
    builder = ReplyKeyboardBuilder()
    
    if is_registered:
        builder.row(
            KeyboardButton(text="🛒 Зробити замовлення"),
            KeyboardButton(text="📋 Мої замовлення"),
        )
        builder.row(
            KeyboardButton(text="👤 Мій профіль"),
            KeyboardButton(text="✏️ Змінити дані"),
        )
    else:
        builder.row(KeyboardButton(text="📝 Реєстрація"))
    
    builder.row(
        KeyboardButton(text="💰 Ціни"),
        KeyboardButton(text="📞 Контакти"),
    )
    
    return builder.as_markup(resize_keyboard=True)


def phone_keyboard() -> ReplyKeyboardMarkup:
    """Клавіатура для запиту телефону."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📱 Надіслати номер телефону", request_contact=True))
    builder.row(KeyboardButton(text="❌ Скасувати"))
    return builder.as_markup(resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавіатура з кнопкою скасування."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Скасувати"))
    return builder.as_markup(resize_keyboard=True)


def water_type_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура вибору типу води."""
    builder = InlineKeyboardBuilder()
    
    for water_type in WaterType:
        builder.row(InlineKeyboardButton(
            text=WATER_TYPE_NAMES[water_type],
            callback_data=f"water_{water_type.value}"
        ))
    
    builder.row(
        InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_order"),
    )
    
    return builder.as_markup()


def quantity_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура вибору кількості пляшок."""
    builder = InlineKeyboardBuilder()
    
    for i in range(1, 6):
        builder.add(InlineKeyboardButton(text=str(i), callback_data=f"qty_{i}"))
    
    builder.row(
        InlineKeyboardButton(text="6+", callback_data="qty_custom"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_water"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_order"),
    )
    
    return builder.as_markup()


def payment_keyboard(config: Config) -> InlineKeyboardMarkup:
    """Клавіатура вибору способу оплати."""
    builder = InlineKeyboardBuilder()
    
    for i, method in enumerate(config.payment_methods):
        builder.row(InlineKeyboardButton(text=method, callback_data=f"pay_{i}"))
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_qty"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_order"),
    )
    
    return builder.as_markup()


def confirm_order_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура підтвердження замовлення."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Підтвердити", callback_data="confirm_order"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_order"),
    )
    return builder.as_markup()


def admin_order_keyboard(order_id: int, status: OrderStatus = OrderStatus.PENDING) -> InlineKeyboardMarkup:
    """Клавіатура керування замовленням для адміна (динамічна в залежності від статусу)."""
    builder = InlineKeyboardBuilder()
    
    if status == OrderStatus.PENDING:
        # Нове замовлення - можна підтвердити або скасувати
        builder.row(
            InlineKeyboardButton(text="✅ Підтвердити", callback_data=f"admin_confirm_{order_id}"),
        )
        builder.row(
            InlineKeyboardButton(text="❌ Скасувати", callback_data=f"admin_cancel_{order_id}"),
        )
    elif status == OrderStatus.CONFIRMED:
        # Підтверджено - можна відправити в доставку або скасувати
        builder.row(
            InlineKeyboardButton(text="🚗 Відправити в доставку", callback_data=f"admin_deliver_{order_id}"),
        )
        builder.row(
            InlineKeyboardButton(text="❌ Скасувати", callback_data=f"admin_cancel_{order_id}"),
        )
    elif status == OrderStatus.DELIVERING:
        # В доставці - можна примусово завершити
        builder.row(
            InlineKeyboardButton(text="✔️ Завершити (примусово)", callback_data=f"admin_complete_{order_id}"),
        )
    # Для COMPLETED і CANCELLED кнопок немає
    
    return builder.as_markup()


def skip_comment_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура для пропуску коментаря."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏭️ Пропустити", callback_data="skip_comment"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_order"),
    )
    return builder.as_markup()


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Головне меню адміністратора."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Замовлення", callback_data="admin_menu_orders"),
    )
    builder.row(
        InlineKeyboardButton(text="💰 Ціни клієнтів", callback_data="admin_menu_prices"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Всі клієнти", callback_data="admin_menu_clients"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Закрити", callback_data="close_admin"),
    )
    return builder.as_markup()


def users_list_keyboard(users: list[User], page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """Клавіатура зі списком користувачів для адміна."""
    builder = InlineKeyboardBuilder()
    
    start = page * per_page
    end = start + per_page
    page_users = users[start:end]
    
    for user in page_users:
        price_text = f" ({user.custom_price} ₴)" if user.custom_price else ""
        builder.row(InlineKeyboardButton(
            text=f"👤 {user.full_name}{price_text}",
            callback_data=f"setprice_user_{user.telegram_id}"
        ))
    
    # Навігація
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"users_page_{page - 1}"))
    if end < len(users):
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"users_page_{page + 1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(InlineKeyboardButton(text="❌ Закрити", callback_data="close_admin"))
    
    return builder.as_markup()


def order_complete_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавіатура для клієнта - підтвердження отримання замовлення."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Замовлення отримано!", callback_data=f"client_received_{order_id}"),
    )
    return builder.as_markup()


def rating_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавіатура для оцінки замовлення."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⭐", callback_data=f"rate_{order_id}_1"),
        InlineKeyboardButton(text="⭐⭐", callback_data=f"rate_{order_id}_2"),
        InlineKeyboardButton(text="⭐⭐⭐", callback_data=f"rate_{order_id}_3"),
    )
    builder.row(
        InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data=f"rate_{order_id}_4"),
        InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data=f"rate_{order_id}_5"),
    )
    return builder.as_markup()


def skip_feedback_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура для пропуску відгуку."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏭️ Пропустити", callback_data="skip_feedback"),
    )
    return builder.as_markup()
