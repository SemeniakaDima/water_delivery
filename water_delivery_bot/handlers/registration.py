"""Обробники реєстрації та профілю."""

import re
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from database import get_user, create_user, update_user
from keyboards import main_menu_keyboard, phone_keyboard, cancel_keyboard
from states import RegistrationStates, EditProfileStates

router = Router()


def normalize_phone(phone: str) -> str:
    """Нормалізація номера телефону."""
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    return '+' + digits if digits else phone


def validate_phone(phone: str) -> bool:
    """Валідація номера телефону."""
    digits = re.sub(r'\D', '', phone)
    return len(digits) >= 10 and len(digits) <= 12


# ============= РЕЄСТРАЦІЯ =============

@router.message(F.text == "📝 Реєстрація")
async def start_registration(message: Message, state: FSMContext):
    """Початок реєстрації."""
    user = await get_user(message.from_user.id)
    if user:
        await message.answer(
            "Ви вже зареєстровані! Використовуйте меню для навігації.",
            reply_markup=main_menu_keyboard(is_registered=True)
        )
        return
    
    await state.set_state(RegistrationStates.waiting_for_name)
    await message.answer(
        "📝 <b>Реєстрація</b>\n\n"
        "Введіть ваше <b>ПІБ</b> (повністю):",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обробка ПІБ."""
    name = message.text.strip()
    
    if len(name) < 3:
        await message.answer("❌ ПІБ занадто коротке. Спробуйте ще раз:")
        return
    
    if len(name) > 100:
        await message.answer("❌ ПІБ занадто довге. Спробуйте ще раз:")
        return
    
    await state.update_data(full_name=name)
    await state.set_state(RegistrationStates.waiting_for_phone)
    
    await message.answer(
        f"✅ Чудово, <b>{name}</b>!\n\n"
        "Тепер введіть ваш <b>номер телефону</b>\n"
        "або натисніть кнопку нижче для надсилання:",
        reply_markup=phone_keyboard(),
        parse_mode="HTML"
    )


@router.message(RegistrationStates.waiting_for_phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    """Обробка телефону через контакт."""
    phone = normalize_phone(message.contact.phone_number)
    await state.update_data(phone=phone)
    await state.set_state(RegistrationStates.waiting_for_address)
    
    await message.answer(
        f"✅ Телефон: <b>{phone}</b>\n\n"
        "Введіть вашу <b>адресу доставки</b>\n"
        "(місто, вулиця, будинок, квартира):",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(RegistrationStates.waiting_for_phone)
async def process_phone_text(message: Message, state: FSMContext):
    """Обробка телефону текстом."""
    if not validate_phone(message.text):
        await message.answer(
            "❌ Невірний формат телефону.\n"
            "Введіть номер у форматі: +380XXXXXXXXX або 0XXXXXXXXX"
        )
        return
    
    phone = normalize_phone(message.text)
    await state.update_data(phone=phone)
    await state.set_state(RegistrationStates.waiting_for_address)
    
    await message.answer(
        f"✅ Телефон: <b>{phone}</b>\n\n"
        "Введіть вашу <b>адресу доставки</b>\n"
        "(місто, вулиця, будинок, квартира):",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(RegistrationStates.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    """Обробка адреси та завершення реєстрації."""
    address = message.text.strip()
    
    if len(address) < 10:
        await message.answer("❌ Адреса занадто коротка. Вкажіть повну адресу:")
        return
    
    if len(address) > 200:
        await message.answer("❌ Адреса занадто довга. Спробуйте скоротити:")
        return
    
    data = await state.get_data()
    
    await create_user(
        telegram_id=message.from_user.id,
        full_name=data["full_name"],
        phone=data["phone"],
        address=address
    )
    
    await state.clear()
    
    await message.answer(
        "🎉 <b>Реєстрацію завершено!</b>\n\n"
        f"👤 ПІБ: {data['full_name']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"📍 Адреса: {address}\n\n"
        "Тепер ви можете робити замовлення!",
        reply_markup=main_menu_keyboard(is_registered=True),
        parse_mode="HTML"
    )


# ============= ПРОФІЛЬ =============

@router.message(F.text == "👤 Мій профіль")
async def show_profile(message: Message):
    """Показати профіль користувача."""
    user = await get_user(message.from_user.id)
    
    if not user:
        await message.answer(
            "Ви ще не зареєстровані.",
            reply_markup=main_menu_keyboard(is_registered=False)
        )
        return
    
    profile_text = (
        "👤 <b>Ваш профіль</b>\n\n"
        f"📋 ПІБ: {user.full_name}\n"
        f"📱 Телефон: {user.phone}\n"
        f"📍 Адреса: {user.address}\n"
        f"📅 Дата реєстрації: {user.created_at.strftime('%d.%m.%Y')}"
    )
    
    await message.answer(profile_text, parse_mode="HTML")


# ============= РЕДАГУВАННЯ ПРОФІЛЮ =============

@router.message(F.text == "✏️ Змінити дані")
async def start_edit_profile(message: Message, state: FSMContext):
    """Початок редагування профілю."""
    user = await get_user(message.from_user.id)
    
    if not user:
        await message.answer(
            "Спочатку пройдіть реєстрацію.",
            reply_markup=main_menu_keyboard(is_registered=False)
        )
        return
    
    await state.update_data(
        current_name=user.full_name,
        current_phone=user.phone,
        current_address=user.address
    )
    await state.set_state(EditProfileStates.waiting_for_name)
    
    await message.answer(
        "✏️ <b>Редагування профілю</b>\n\n"
        f"Поточне ПІБ: <b>{user.full_name}</b>\n\n"
        "Введіть нове ПІБ або надішліть крапку (.) щоб залишити поточне:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(EditProfileStates.waiting_for_name)
async def edit_name(message: Message, state: FSMContext):
    """Редагування ПІБ."""
    data = await state.get_data()
    
    if message.text.strip() == ".":
        name = data["current_name"]
    else:
        name = message.text.strip()
        if len(name) < 3 or len(name) > 100:
            await message.answer("❌ Некоректне ПІБ. Спробуйте ще раз:")
            return
    
    await state.update_data(full_name=name)
    await state.set_state(EditProfileStates.waiting_for_phone)
    
    await message.answer(
        f"✅ ПІБ: <b>{name}</b>\n\n"
        f"Поточний телефон: <b>{data['current_phone']}</b>\n\n"
        "Введіть новий телефон або надішліть крапку (.) щоб залишити поточний:",
        reply_markup=phone_keyboard(),
        parse_mode="HTML"
    )


@router.message(EditProfileStates.waiting_for_phone, F.contact)
async def edit_phone_contact(message: Message, state: FSMContext):
    """Редагування телефону через контакт."""
    phone = normalize_phone(message.contact.phone_number)
    data = await state.get_data()
    
    await state.update_data(phone=phone)
    await state.set_state(EditProfileStates.waiting_for_address)
    
    await message.answer(
        f"✅ Телефон: <b>{phone}</b>\n\n"
        f"Поточна адреса: <b>{data['current_address']}</b>\n\n"
        "Введіть нову адресу або надішліть крапку (.) щоб залишити поточну:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(EditProfileStates.waiting_for_phone)
async def edit_phone_text(message: Message, state: FSMContext):
    """Редагування телефону текстом."""
    data = await state.get_data()
    
    if message.text.strip() == ".":
        phone = data["current_phone"]
    else:
        if not validate_phone(message.text):
            await message.answer("❌ Невірний формат телефону. Спробуйте ще раз:")
            return
        phone = normalize_phone(message.text)
    
    await state.update_data(phone=phone)
    await state.set_state(EditProfileStates.waiting_for_address)
    
    await message.answer(
        f"✅ Телефон: <b>{phone}</b>\n\n"
        f"Поточна адреса: <b>{data['current_address']}</b>\n\n"
        "Введіть нову адресу або надішліть крапку (.) щоб залишити поточну:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(EditProfileStates.waiting_for_address)
async def edit_address(message: Message, state: FSMContext):
    """Редагування адреси та збереження профілю."""
    data = await state.get_data()
    
    if message.text.strip() == ".":
        address = data["current_address"]
    else:
        address = message.text.strip()
        if len(address) < 10 or len(address) > 200:
            await message.answer("❌ Некоректна адреса. Спробуйте ще раз:")
            return
    
    await update_user(
        telegram_id=message.from_user.id,
        full_name=data["full_name"],
        phone=data["phone"],
        address=address
    )
    
    await state.clear()
    
    await message.answer(
        "✅ <b>Профіль оновлено!</b>\n\n"
        f"👤 ПІБ: {data['full_name']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"📍 Адреса: {address}",
        reply_markup=main_menu_keyboard(is_registered=True),
        parse_mode="HTML"
    )
