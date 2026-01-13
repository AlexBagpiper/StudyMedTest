"""
Скрипт для создания учетной записи преподавателя
"""

import asyncio
import sys
from getpass import getpass

from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.user import User, Role


async def create_teacher():
    """Создание учетной записи преподавателя"""
    
    print("=== Создание учетной записи преподавателя ===\n")
    
    # Ввод данных
    email = input("Email: ").strip()
    if not email:
        print("❌ Email обязателен!")
        sys.exit(1)
    
    last_name = input("Фамилия: ").strip()
    if not last_name:
        print("❌ Фамилия обязательна!")
        sys.exit(1)
    
    first_name = input("Имя: ").strip()
    if not first_name:
        print("❌ Имя обязательно!")
        sys.exit(1)
    
    middle_name = input("Отчество (необязательно): ").strip() or None
    
    password = getpass("Пароль: ")
    if len(password) < 6:
        print("❌ Пароль должен быть не менее 6 символов!")
        sys.exit(1)
    
    password_confirm = getpass("Подтвердите пароль: ")
    if password != password_confirm:
        print("❌ Пароли не совпадают!")
        sys.exit(1)
    
    # Создание пользователя
    async with async_session_maker() as session:
        # Проверка существования
        result = await session.execute(
            select(User).where(User.email == email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"❌ Пользователь с email {email} уже существует!")
            sys.exit(1)
        
        # Создание
        teacher = User(
            email=email,
            password_hash=get_password_hash(password),
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
            role=Role.TEACHER,
            is_active=True,
            is_verified=True,
        )
        
        session.add(teacher)
        await session.commit()
        
        print(f"\n✅ Преподаватель успешно создан!")
        print(f"   Email: {email}")
        print(f"   ФИО: {last_name} {first_name} {middle_name or ''}")
        print(f"   Роль: teacher")


if __name__ == "__main__":
    asyncio.run(create_teacher())
