"""Стани FSM для діалогів."""

from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Стани реєстрації користувача."""
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()


class EditProfileStates(StatesGroup):
    """Стани редагування профілю."""
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()


class OrderStates(StatesGroup):
    """Стани оформлення замовлення."""
    waiting_for_water_type = State()
    waiting_for_quantity = State()
    waiting_for_custom_quantity = State()
    waiting_for_payment = State()
    waiting_for_comment = State()
    waiting_for_confirmation = State()


class RatingStates(StatesGroup):
    """Стани оцінки замовлення."""
    waiting_for_rating = State()
    waiting_for_feedback = State()


class AdminStates(StatesGroup):
    """Стани адмін-панелі."""
    waiting_for_price = State()
