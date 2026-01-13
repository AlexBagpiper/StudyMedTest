import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select


async def create_admin():
    async with AsyncSessionLocal() as db:
        # Проверяем, есть ли уже админ
        result = await db.execute(
            select(User).where(User.email == 'admin@example.com')
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print('[!] Admin уже существует!')
            return
        
        admin = User(
            email='admin@example.com',
            password_hash=get_password_hash('admin123'),
            last_name='Администратор',
            first_name='Системы',
            middle_name=None,
            role='admin',
            is_active=True,
            is_verified=True
        )
        db.add(admin)
        await db.commit()
        print('[OK] Администратор создан успешно!')
        print('   Email: admin@example.com')
        print('   Пароль: admin123')
        print('   [!] ОБЯЗАТЕЛЬНО смените пароль после первого входа!')


if __name__ == '__main__':
    asyncio.run(create_admin())