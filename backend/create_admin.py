import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select


from app.core.config import settings

async def create_admin():
    async with AsyncSessionLocal() as db:
        # Проверяем, есть ли уже админ
        result = await db.execute(
            select(User).where(User.email == settings.FIRST_ADMIN_EMAIL)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f'[!] Admin {settings.FIRST_ADMIN_EMAIL} уже существует!')
            return
        
        admin = User(
            email=settings.FIRST_ADMIN_EMAIL,
            password_hash=get_password_hash(settings.FIRST_ADMIN_PASSWORD),
            last_name='Администратор',
            first_name='Системы',
            middle_name=None,
            role='admin',
            is_active=True,
            is_verified=True
        )
        db.add(admin)
        await db.commit()
        print(f'[OK] Администратор создан успешно!')
        print(f'   Email: {settings.FIRST_ADMIN_EMAIL}')
        print(f'   Пароль: {settings.FIRST_ADMIN_PASSWORD}')
        print('   [!] ОБЯЗАТЕЛЬНО смените пароль после первого входа!')


if __name__ == '__main__':
    asyncio.run(create_admin())