"""Обробники замовлень."""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import (
    get_user, create_order, get_user_orders, get_order_with_user,
    set_order_rating, update_order_status,
    OrderStatus, WaterType, WATER_TYPE_NAMES
)
from keyboards import (
    main_menu_keyboard,
    water_type_keyboard,
    quantity_keyboard,
    payment_keyboard,
    confirm_order_keyboard,
    skip_comment_keyboard,
    rating_keyboard,
    skip_feedback_keyboard,
)
from states import OrderStates, RatingStates
from config import Config

router = Router()
logger = logging.getLogger(__name__)


def get_user_price(user, config: Config) -> int:
    """Отримати ціну для користувача (індивідуальну або за замовчуванням)."""
    if user.custom_price is not None:
        return user.custom_price
    return config.default_bottle_price


# ============= СТВОРЕННЯ ЗАМОВЛЕННЯ =============

@router.message(F.text == "🛒 Зробити замовлення")
async def start_order(message: Message, state: FSMContext, config: Config):
    """Початок оформлення замовлення."""
    user = await get_user(message.from_user.id)
    
    if not user:
        await message.answer(
            "❌ Для оформлення замовлення необхідно зареєструватися.",
            reply_markup=main_menu_keyboard(is_registered=False)
        )
        return
    
    price = get_user_price(user, config)
    await state.update_data(bottle_price=price)
    await state.set_state(OrderStates.waiting_for_water_type)
    
    await message.answer(
        "🛒 <b>Оформлення замовлення</b>\n\n"
        f"💰 Ваша ціна: <b>{price} ₴</b> за пляшку\n"
        "🚚 Доставка: <b>безкоштовно</b>\n\n"
        "Оберіть тип води:",
        reply_markup=water_type_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("water_"), OrderStates.waiting_for_water_type)
async def process_water_type(callback: CallbackQuery, state: FSMContext, config: Config):
    """Обробка вибору типу води."""
    water_type_value = callback.data.split("_", 1)[1]
    water_type = WaterType(water_type_value)
    
    await state.update_data(water_type=water_type)
    await state.set_state(OrderStates.waiting_for_quantity)
    
    data = await state.get_data()
    price = data["bottle_price"]
    
    await callback.message.edit_text(
        f"🛒 <b>Оформлення замовлення</b>\n\n"
        f"💧 Тип: <b>{WATER_TYPE_NAMES[water_type]}</b>\n"
        f"💰 Ціна: <b>{price} ₴</b> за пляшку\n\n"
        "Оберіть кількість пляшок:",
        reply_markup=quantity_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_to_water")
async def back_to_water_type(callback: CallbackQuery, state: FSMContext, config: Config):
    """Повернутися до вибору типу води."""
    await state.set_state(OrderStates.waiting_for_water_type)
    
    data = await state.get_data()
    price = data.get("bottle_price", config.default_bottle_price)
    
    await callback.message.edit_text(
        "🛒 <b>Оформлення замовлення</b>\n\n"
        f"💰 Ваша ціна: <b>{price} ₴</b> за пляшку\n"
        "🚚 Доставка: <b>безкоштовно</b>\n\n"
        "Оберіть тип води:",
        reply_markup=water_type_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("qty_"), OrderStates.waiting_for_quantity)
async def process_quantity(callback: CallbackQuery, state: FSMContext, config: Config):
    """Обробка вибору кількості."""
    qty_str = callback.data.split("_")[1]
    
    if qty_str == "custom":
        await state.set_state(OrderStates.waiting_for_custom_quantity)
        await callback.message.edit_text(
            "Введіть потрібну кількість пляшок (число):"
        )
        return
    
    quantity = int(qty_str)
    await state.update_data(quantity=quantity)
    await state.set_state(OrderStates.waiting_for_payment)
    
    data = await state.get_data()
    price = data["bottle_price"]
    water_type = data["water_type"]
    total = quantity * price
    
    await callback.message.edit_text(
        f"📦 Тип: <b>{WATER_TYPE_NAMES[water_type]}</b>\n"
        f"📦 Кількість: <b>{quantity} пл.</b>\n"
        f"💰 {quantity} × {price} ₴ = <b>{total} ₴</b>\n"
        f"🚚 Доставка: безкоштовно\n\n"
        "Оберіть спосіб оплати:",
        reply_markup=payment_keyboard(config),
        parse_mode="HTML"
    )


@router.message(OrderStates.waiting_for_custom_quantity)
async def process_custom_quantity(message: Message, state: FSMContext, config: Config):
    """Обробка довільної кількості."""
    try:
        quantity = int(message.text.strip())
        if quantity < 1 or quantity > 100:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введіть число від 1 до 100:")
        return
    
    await state.update_data(quantity=quantity)
    await state.set_state(OrderStates.waiting_for_payment)
    
    data = await state.get_data()
    price = data["bottle_price"]
    water_type = data["water_type"]
    total = quantity * price
    
    await message.answer(
        f"📦 Тип: <b>{WATER_TYPE_NAMES[water_type]}</b>\n"
        f"📦 Кількість: <b>{quantity} пл.</b>\n"
        f"💰 {quantity} × {price} ₴ = <b>{total} ₴</b>\n"
        f"🚚 Доставка: безкоштовно\n\n"
        "Оберіть спосіб оплати:",
        reply_markup=payment_keyboard(config),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_to_qty")
async def back_to_quantity(callback: CallbackQuery, state: FSMContext, config: Config):
    """Повернутися до вибору кількості."""
    await state.set_state(OrderStates.waiting_for_quantity)
    
    data = await state.get_data()
    price = data["bottle_price"]
    water_type = data["water_type"]
    
    await callback.message.edit_text(
        f"🛒 <b>Оформлення замовлення</b>\n\n"
        f"💧 Тип: <b>{WATER_TYPE_NAMES[water_type]}</b>\n"
        f"💰 Ціна: <b>{price} ₴</b> за пляшку\n\n"
        "Оберіть кількість пляшок:",
        reply_markup=quantity_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("pay_"), OrderStates.waiting_for_payment)
async def process_payment(callback: CallbackQuery, state: FSMContext, config: Config):
    """Обробка вибору способу оплати."""
    pay_idx = int(callback.data.split("_")[1])
    payment_method = config.payment_methods[pay_idx]
    
    await state.update_data(payment_method=payment_method)
    await state.set_state(OrderStates.waiting_for_comment)
    
    await callback.message.edit_text(
        f"💳 Спосіб оплати: <b>{payment_method}</b>\n\n"
        "Додайте коментар до замовлення (час доставки, під'їзд, домофон тощо)\n"
        "або натисніть «Пропустити»:",
        reply_markup=skip_comment_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "skip_comment", OrderStates.waiting_for_comment)
async def skip_comment(callback: CallbackQuery, state: FSMContext, config: Config):
    """Пропустити коментар."""
    await state.update_data(comment=None)
    await show_confirmation(callback.message, state, config, telegram_id=callback.from_user.id, edit=True)


@router.message(OrderStates.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext, config: Config):
    """Обробка коментаря."""
    comment = message.text.strip()[:500]
    await state.update_data(comment=comment)
    await show_confirmation(message, state, config, telegram_id=message.from_user.id, edit=False)


async def show_confirmation(message: Message, state: FSMContext, config: Config, telegram_id: int, edit: bool = False):
    """Показати підтвердження замовлення."""
    data = await state.get_data()
    user = await get_user(telegram_id)
    
    quantity = data["quantity"]
    price = data["bottle_price"]
    water_type = data["water_type"]
    total = quantity * price
    
    comment_text = f"\n💬 Коментар: {data.get('comment')}" if data.get("comment") else ""
    
    await state.update_data(total_price=total)
    await state.set_state(OrderStates.waiting_for_confirmation)
    
    confirmation_text = (
        "📋 <b>Підтвердження замовлення</b>\n\n"
        f"👤 {user.full_name}\n"
        f"📱 {user.phone}\n"
        f"📍 {user.address}\n\n"
        f"💧 {WATER_TYPE_NAMES[water_type]}\n"
        f"📦 Кількість: {quantity} пл. × {price} ₴ = {total} ₴\n"
        f"🚚 Доставка: безкоштовно\n"
        f"💳 Оплата: {data['payment_method']}\n"
        f"{comment_text}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💵 <b>РАЗОМ: {total} ₴</b>\n\n"
        "Підтвердіть замовлення:"
    )
    
    if edit:
        await message.edit_text(
            confirmation_text,
            reply_markup=confirm_order_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            confirmation_text,
            reply_markup=confirm_order_keyboard(),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "confirm_order", OrderStates.waiting_for_confirmation)
async def confirm_order(callback: CallbackQuery, state: FSMContext, config: Config):
    """Підтвердження замовлення."""
    data = await state.get_data()
    user = await get_user(callback.from_user.id)
    
    order = await create_order(
        user_id=user.id,
        water_type=data["water_type"],
        quantity=data["quantity"],
        total_price=data["total_price"],
        payment_method=data["payment_method"],
        comment=data.get("comment")
    )
    
    await state.clear()
    
    water_type_name = WATER_TYPE_NAMES[data["water_type"]]
    
    await callback.message.edit_text(
        f"✅ <b>Замовлення #{order.id} оформлено!</b>\n\n"
        f"💧 {water_type_name}\n"
        f"📦 {data['quantity']} пл. на суму {data['total_price']} ₴\n"
        f"💳 {data['payment_method']}\n\n"
        "Менеджер зв'яжеться з вами для підтвердження "
        "та уточнення часу доставки.\n\n"
        "Дякуємо за замовлення! 💙",
        parse_mode="HTML"
    )
    
    await callback.message.answer(
        "Оберіть дію:",
        reply_markup=main_menu_keyboard(is_registered=True)
    )
    
    # Сповіщення адмінів
    bot = callback.bot
    from keyboards import admin_order_keyboard
    
    order_notification = (
        f"🆕 <b>Нове замовлення #{order.id}</b>\n\n"
        f"👤 {user.full_name}\n"
        f"📱 {user.phone}\n"
        f"📍 {user.address}\n\n"
        f"💧 {water_type_name}\n"
        f"📦 {data['quantity']} пл.\n"
        f"💵 {data['total_price']} ₴\n"
        f"💳 {data['payment_method']}\n"
        f"💬 {data.get('comment') or 'без коментаря'}"
    )
    
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                order_notification,
                reply_markup=admin_order_keyboard(order.id),
                parse_mode="HTML"
            )
        except Exception:
            pass
    
    # Сповіщення в чат замовлень
    ORDERS_CHAT_ID = -1002682380858
    try:
        await bot.send_message(
            chat_id=ORDERS_CHAT_ID,
            text=order_notification,
            reply_markup=admin_order_keyboard(order.id),
            parse_mode="HTML"
        )
        logger.info(f"Замовлення #{order.id} надіслано в чат {ORDERS_CHAT_ID}")
    except Exception as e:
        logger.error(f"Помилка відправки в чат {ORDERS_CHAT_ID}: {e}")


@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    """Скасування замовлення."""
    await state.clear()
    
    await callback.message.edit_text("❌ Замовлення скасовано.")
    await callback.message.answer(
        "Ви в головному меню.",
        reply_markup=main_menu_keyboard(is_registered=True)
    )


# ============= МОЇ ЗАМОВЛЕННЯ =============

@router.message(F.text == "📋 Мої замовлення")
async def show_my_orders(message: Message):
    """Показати замовлення користувача."""
    user = await get_user(message.from_user.id)
    
    if not user:
        await message.answer(
            "Ви не зареєстровані.",
            reply_markup=main_menu_keyboard(is_registered=False)
        )
        return
    
    orders = await get_user_orders(message.from_user.id)
    
    if not orders:
        await message.answer(
            "📋 У вас поки немає замовлень.\n\n"
            "Натисніть «🛒 Зробити замовлення» щоб оформити перше замовлення!"
        )
        return
    
    status_icons = {
        OrderStatus.PENDING: "⏳",
        OrderStatus.CONFIRMED: "✅",
        OrderStatus.DELIVERING: "🚗",
        OrderStatus.COMPLETED: "✔️",
        OrderStatus.CANCELLED: "❌",
    }
    
    status_names = {
        OrderStatus.PENDING: "Очікує підтвердження",
        OrderStatus.CONFIRMED: "Підтверджено",
        OrderStatus.DELIVERING: "У доставці",
        OrderStatus.COMPLETED: "Виконано",
        OrderStatus.CANCELLED: "Скасовано",
    }
    
    orders_text = "📋 <b>Ваші замовлення</b>\n\n"
    
    for order in orders:
        icon = status_icons.get(order.status, "❓")
        status_name = status_names.get(order.status, "Невідомо")
        water_name = WATER_TYPE_NAMES.get(order.water_type, "Вода")
        
        orders_text += (
            f"<b>Замовлення #{order.id}</b> {icon}\n"
            f"📅 {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"💧 {water_name}\n"
            f"📦 {order.quantity} пл. • {order.total_price} ₴\n"
            f"📊 Статус: {status_name}\n"
            "───────────────\n"
        )
    
    await message.answer(orders_text, parse_mode="HTML")


# ============= ОЦІНКА ЗАМОВЛЕННЯ =============

@router.callback_query(F.data.startswith("client_received_"))
async def client_received_order(callback: CallbackQuery, state: FSMContext, config: Config):
    """Клієнт підтвердив отримання замовлення."""
    order_id = int(callback.data.split("_")[2])
    
    # Перевіряємо, що замовлення існує і належить цьому користувачу
    order_data = await get_order_with_user(order_id)
    
    if not order_data:
        await callback.answer("❌ Замовлення не знайдено", show_alert=True)
        return
    
    order, user = order_data
    
    if user.telegram_id != callback.from_user.id:
        await callback.answer("❌ Це не ваше замовлення", show_alert=True)
        return
    
    if order.status != OrderStatus.DELIVERING:
        await callback.answer("❌ Замовлення вже оброблено", show_alert=True)
        return
    
    # Оновлюємо статус на COMPLETED
    await update_order_status(order_id, OrderStatus.COMPLETED)
    
    # Зберігаємо order_id для оцінки
    await state.update_data(rating_order_id=order_id)
    await state.set_state(RatingStates.waiting_for_rating)
    
    await callback.message.edit_text(
        f"🎉 <b>Чудово! Замовлення #{order_id} отримано!</b>\n\n"
        "Будь ласка, оцініть якість нашого сервісу:\n\n"
        "⭐ — погано\n"
        "⭐⭐⭐ — нормально\n"
        "⭐⭐⭐⭐⭐ — відмінно!",
        reply_markup=rating_keyboard(order_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.regexp(r"^rate_\d+_[1-5]$"))
async def process_rating(callback: CallbackQuery, state: FSMContext, config: Config):
    """Обробка оцінки від клієнта."""
    parts = callback.data.split("_")
    order_id = int(parts[1])
    rating = int(parts[2])
    
    await state.update_data(rating_order_id=order_id, rating=rating)
    
    if rating <= 2:
        # Погана оцінка - обов'язково просимо відгук
        await state.set_state(RatingStates.waiting_for_feedback)
        await callback.message.edit_text(
            f"😔 Нам дуже шкода, що ви незадоволені!\n\n"
            "Будь ласка, напишіть, що саме вам не сподобалось. "
            "Ми обов'язково врахуємо ваші зауваження і покращимо сервіс!",
            parse_mode="HTML"
        )
    else:
        # Хороша оцінка - відгук необов'язковий
        await state.set_state(RatingStates.waiting_for_feedback)
        await callback.message.edit_text(
            f"{'⭐' * rating} Дякуємо за оцінку!\n\n"
            "Хочете залишити відгук? Напишіть його нижче,\n"
            "або натисніть «Пропустити»:",
            reply_markup=skip_feedback_keyboard(),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "skip_feedback", RatingStates.waiting_for_feedback)
async def skip_feedback(callback: CallbackQuery, state: FSMContext, config: Config):
    """Пропустити відгук."""
    data = await state.get_data()
    order_id = data.get("rating_order_id")
    rating = data.get("rating")
    
    if order_id and rating:
        await set_order_rating(order_id, rating, None)
    
    await state.clear()
    
    await callback.message.edit_text(
        "💙 <b>Дякуємо за вашу оцінку!</b>\n\n"
        "Будемо раді бачити вас знову!",
        parse_mode="HTML"
    )


@router.message(RatingStates.waiting_for_feedback)
async def process_feedback(message: Message, state: FSMContext, config: Config):
    """Обробка відгуку від клієнта."""
    data = await state.get_data()
    order_id = data.get("rating_order_id")
    rating = data.get("rating")
    feedback = message.text.strip()[:1000]  # Обмеження довжини
    
    if order_id and rating:
        await set_order_rating(order_id, rating, feedback)
        
        # Якщо погана оцінка - сповіщаємо адмінів
        if rating <= 2:
            order_data = await get_order_with_user(order_id)
            if order_data:
                order, user = order_data
                
                bot = message.bot
                for admin_id in config.admin_ids:
                    try:
                        await bot.send_message(
                            admin_id,
                            f"⚠️ <b>УВАГА! Негативний відгук!</b>\n\n"
                            f"Замовлення: #{order_id}\n"
                            f"Клієнт: {user.full_name}\n"
                            f"Телефон: {user.phone}\n"
                            f"Оцінка: {'⭐' * rating}\n\n"
                            f"💬 Відгук:\n<i>{feedback}</i>\n\n"
                            "Рекомендуємо зв'язатись з клієнтом!",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
    
    await state.clear()
    
    if rating and rating <= 2:
        await message.answer(
            "💙 <b>Дякуємо за ваш відгук!</b>\n\n"
            "Ми обов'язково розглянемо ваші зауваження "
            "та зробимо все можливе для покращення сервісу.\n\n"
            "Будемо раді бачити вас знову!",
            reply_markup=main_menu_keyboard(is_registered=True),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "💙 <b>Дякуємо за ваш відгук!</b>\n\n"
            "Ваша думка дуже важлива для нас!\n"
            "Будемо раді бачити вас знову!",
            reply_markup=main_menu_keyboard(is_registered=True),
            parse_mode="HTML"
        )
