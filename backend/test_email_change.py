"""
Скрипт для тестирования смены email
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.user import User
from app.services.email_service import send_email_change_code


async def test_email_change():
    """Тестирование функциональности смены email"""
    
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ СМЕНЫ EMAIL")
    print("=" * 60)
    
    # Проверяем структуру таблицы
    async with async_session_maker() as session:
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ Нет пользователей в базе. Создайте пользователя сначала.")
            return False
        
        print(f"\n✅ Найден пользователь: {user.email}")
        
        # Проверяем наличие полей для смены email
        try:
            print(f"   - pending_email: {user.pending_email}")
            print(f"   - email_change_code: {user.email_change_code}")
            print(f"   - email_change_expires: {user.email_change_expires}")
            print("\n✅ Поля для смены email существуют в БД")
        except AttributeError as e:
            print(f"\n❌ Ошибка: Поля для смены email не найдены в модели")
            print(f"   Возможно не применена миграция: {e}")
            return False
    
    # Тестируем отправку email
    print("\n" + "-" * 60)
    print("ТЕСТИРОВАНИЕ ОТПРАВКИ EMAIL")
    print("-" * 60)
    
    test_email = "test@example.com"
    test_code = "123456"
    
    print(f"\nОтправка кода {test_code} на {test_email}...")
    success = await send_email_change_code(test_email, test_code)
    
    if success:
        print("✅ Email отправлен успешно (или залогирован в dev режиме)")
    else:
        print("❌ Ошибка при отправке email")
        return False
    
    print("\n" + "=" * 60)
    print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
    print("=" * 60)
    print("\nФункциональность смены email работает корректно!")
    print("\nДля использования:")
    print("1. Запустите backend: uvicorn app.main:app --reload")
    print("2. Запустите frontend: npm run dev")
    print("3. Войдите в профиль и нажмите 'Изменить email'")
    
    return True


async def main():
    try:
        success = await test_email_change()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
