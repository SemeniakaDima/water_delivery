"""Модуль роботи з базою даних SQLite."""

import aiosqlite
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


class OrderStatus(Enum):
    """Статуси замовлення."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DELIVERING = "delivering"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WaterType(Enum):
    """Типи води."""
    EFFECT = "effect"
    EFFECT_COFFEE = "effect_coffee"


WATER_TYPE_NAMES = {
    WaterType.EFFECT: "💧 Вода Ефект 19л",
    WaterType.EFFECT_COFFEE: "☕ Вода Ефект для кави 19л",
}


@dataclass
class User:
    """Модель користувача."""
    id: int
    telegram_id: int
    full_name: str
    phone: str
    address: str
    created_at: datetime
    custom_price: int | None = None


@dataclass
class Order:
    """Модель замовлення."""
    id: int
    user_id: int
    water_type: WaterType
    quantity: int
    total_price: int
    payment_method: str
    status: OrderStatus
    created_at: datetime
    comment: str | None = None
    confirmed_at: datetime | None = None
    delivered_at: datetime | None = None
    completed_at: datetime | None = None
    rating: int | None = None
    feedback: str | None = None


DATABASE_PATH = Path(__file__).parent / "data" / "water_delivery.db"


def _safe_get(row, key, default=None):
    """Безпечне отримання значення з Row."""
    try:
        value = row[key]
        return value if value is not None else default
    except (KeyError, IndexError):
        return default


def _parse_order(row) -> Order:
    """Парсинг рядка в Order."""
    confirmed_at_str = _safe_get(row, "confirmed_at")
    delivered_at_str = _safe_get(row, "delivered_at")
    completed_at_str = _safe_get(row, "completed_at")
    
    return Order(
        id=row["id"],
        user_id=row["user_id"],
        water_type=WaterType(row["water_type"]) if row["water_type"] else WaterType.EFFECT,
        quantity=row["quantity"],
        total_price=row["total_price"],
        payment_method=row["payment_method"],
        status=OrderStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        comment=row["comment"],
        confirmed_at=datetime.fromisoformat(confirmed_at_str) if confirmed_at_str else None,
        delivered_at=datetime.fromisoformat(delivered_at_str) if delivered_at_str else None,
        completed_at=datetime.fromisoformat(completed_at_str) if completed_at_str else None,
        rating=_safe_get(row, "rating"),
        feedback=_safe_get(row, "feedback"),
    )


def _parse_user(row) -> User:
    """Парсинг рядка в User."""
    return User(
        id=row["id"],
        telegram_id=row["telegram_id"],
        full_name=row["full_name"],
        phone=row["phone"],
        address=row["address"],
        created_at=datetime.fromisoformat(row["created_at"]),
        custom_price=_safe_get(row, "custom_price"),
    )


async def init_db():
    """Ініціалізація бази даних."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                custom_price INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                water_type TEXT DEFAULT 'effect',
                quantity INTEGER NOT NULL,
                total_price INTEGER NOT NULL,
                payment_method TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                comment TEXT,
                confirmed_at TIMESTAMP,
                delivered_at TIMESTAMP,
                completed_at TIMESTAMP,
                rating INTEGER,
                feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Міграції: додаємо нові колонки якщо їх немає
        migrations = [
            "ALTER TABLE users ADD COLUMN custom_price INTEGER",
            "ALTER TABLE orders ADD COLUMN water_type TEXT DEFAULT 'effect'",
            "ALTER TABLE orders ADD COLUMN confirmed_at TIMESTAMP",
            "ALTER TABLE orders ADD COLUMN delivered_at TIMESTAMP",
            "ALTER TABLE orders ADD COLUMN completed_at TIMESTAMP",
            "ALTER TABLE orders ADD COLUMN rating INTEGER",
            "ALTER TABLE orders ADD COLUMN feedback TEXT",
        ]
        
        for migration in migrations:
            try:
                await db.execute(migration)
            except Exception:
                pass  # Колонка вже існує
        
        await db.commit()


async def get_user(telegram_id: int) -> User | None:
    """Отримання користувача по telegram_id."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return _parse_user(row) if row else None


async def get_user_by_id(user_id: int) -> User | None:
    """Отримання користувача по id."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return _parse_user(row) if row else None


async def create_user(telegram_id: int, full_name: str, phone: str, address: str) -> User:
    """Створення нового користувача."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO users (telegram_id, full_name, phone, address)
               VALUES (?, ?, ?, ?)""",
            (telegram_id, full_name, phone, address)
        )
        await db.commit()
        
        return User(
            id=cursor.lastrowid,
            telegram_id=telegram_id,
            full_name=full_name,
            phone=phone,
            address=address,
            created_at=datetime.now(),
            custom_price=None
        )


async def update_user(telegram_id: int, full_name: str, phone: str, address: str) -> None:
    """Оновлення даних користувача."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """UPDATE users SET full_name = ?, phone = ?, address = ?
               WHERE telegram_id = ?""",
            (full_name, phone, address, telegram_id)
        )
        await db.commit()


async def set_user_price(telegram_id: int, price: int | None) -> None:
    """Встановлення індивідуальної ціни для користувача."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET custom_price = ? WHERE telegram_id = ?",
            (price, telegram_id)
        )
        await db.commit()


async def get_all_users() -> list[User]:
    """Отримання всіх користувачів."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users ORDER BY full_name")
        rows = await cursor.fetchall()
        return [_parse_user(row) for row in rows]


async def create_order(
    user_id: int,
    water_type: WaterType,
    quantity: int,
    total_price: int,
    payment_method: str,
    comment: str | None = None
) -> Order:
    """Створення нового замовлення."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO orders (user_id, water_type, quantity, total_price, payment_method, comment)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, water_type.value, quantity, total_price, payment_method, comment)
        )
        await db.commit()
        
        return Order(
            id=cursor.lastrowid,
            user_id=user_id,
            water_type=water_type,
            quantity=quantity,
            total_price=total_price,
            payment_method=payment_method,
            status=OrderStatus.PENDING,
            created_at=datetime.now(),
            comment=comment
        )


async def get_order(order_id: int) -> Order | None:
    """Отримання замовлення по id."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        return _parse_order(row) if row else None


async def get_user_orders(telegram_id: int, limit: int = 10) -> list[Order]:
    """Отримання замовлень користувача."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT o.* FROM orders o
               JOIN users u ON o.user_id = u.id
               WHERE u.telegram_id = ?
               ORDER BY o.created_at DESC
               LIMIT ?""",
            (telegram_id, limit)
        )
        rows = await cursor.fetchall()
        return [_parse_order(row) for row in rows]


async def get_all_pending_orders() -> list[tuple[Order, User]]:
    """Отримання всіх очікуючих замовлень (для адміна)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT o.*, u.telegram_id as u_telegram_id, u.full_name as u_full_name, 
                      u.phone as u_phone, u.address as u_address, 
                      u.custom_price as u_custom_price, u.created_at as u_created_at
               FROM orders o
               JOIN users u ON o.user_id = u.id
               WHERE o.status IN ('pending', 'confirmed', 'delivering')
               ORDER BY o.created_at ASC"""
        )
        rows = await cursor.fetchall()
        
        result = []
        for row in rows:
            order = _parse_order(row)
            user = User(
                id=row["user_id"],
                telegram_id=row["u_telegram_id"],
                full_name=row["u_full_name"],
                phone=row["u_phone"],
                address=row["u_address"],
                created_at=datetime.fromisoformat(row["u_created_at"]),
                custom_price=row["u_custom_price"]
            )
            result.append((order, user))
        
        return result


async def update_order_status(order_id: int, status: OrderStatus) -> None:
    """Оновлення статусу замовлення."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Додаємо час для відповідного статусу
        timestamp_field = None
        if status == OrderStatus.CONFIRMED:
            timestamp_field = "confirmed_at"
        elif status == OrderStatus.DELIVERING:
            timestamp_field = "delivered_at"
        elif status == OrderStatus.COMPLETED:
            timestamp_field = "completed_at"
        
        if timestamp_field:
            await db.execute(
                f"UPDATE orders SET status = ?, {timestamp_field} = ? WHERE id = ?",
                (status.value, datetime.now().isoformat(), order_id)
            )
        else:
            await db.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                (status.value, order_id)
            )
        await db.commit()


async def set_order_rating(order_id: int, rating: int, feedback: str | None = None) -> None:
    """Встановлення оцінки замовлення."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE orders SET rating = ?, feedback = ?, completed_at = ? WHERE id = ?",
            (rating, feedback, datetime.now().isoformat(), order_id)
        )
        await db.commit()


async def get_order_with_user(order_id: int) -> tuple[Order, User] | None:
    """Отримання замовлення з даними користувача."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT o.*, u.telegram_id as u_telegram_id, u.full_name as u_full_name, 
                      u.phone as u_phone, u.address as u_address, 
                      u.custom_price as u_custom_price, u.created_at as u_created_at
               FROM orders o
               JOIN users u ON o.user_id = u.id
               WHERE o.id = ?""",
            (order_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            return None
        
        order = _parse_order(row)
        user = User(
            id=row["user_id"],
            telegram_id=row["u_telegram_id"],
            full_name=row["u_full_name"],
            phone=row["u_phone"],
            address=row["u_address"],
            created_at=datetime.fromisoformat(row["u_created_at"]),
            custom_price=row["u_custom_price"]
        )
        return order, user
