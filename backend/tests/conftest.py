"""
Pytest configuration and fixtures
"""

import asyncio
import uuid
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.user import User
from app.core.security import get_password_hash

# Используем основную БД, но через транзакции. 
# Это безопаснее, если не удается создать тестовую БД.
TEST_DATABASE_URL = settings.async_database_url

# Create async test engine
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)

# Create async session maker
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Ensure tables exist"""
    async with test_engine.begin() as conn:
        # Мы НЕ удаляем таблицы, только создаем если их нет
        await conn.run_sync(Base.metadata.create_all)
    yield

@pytest.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with transaction rollback"""
    # Используем одну транзакцию на весь тест
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        async with TestSessionLocal(bind=conn) as session:
            yield session
            await session.rollback()
        await trans.rollback()


@pytest.fixture(scope="function")
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client"""
    
    async def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db: AsyncSession) -> User:
    """Create test user (student)"""
    user = User(
        email=f"test_student_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=get_password_hash("testpassword"),
        last_name="Тестов",
        first_name="Тест",
        middle_name="Тестович",
        role="student",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def test_teacher(db: AsyncSession) -> User:
    """Create test teacher"""
    user = User(
        email=f"test_teacher_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=get_password_hash("teacherpassword"),
        last_name="Учителев",
        first_name="Учитель",
        middle_name="Учителевич",
        role="teacher",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def test_admin(db: AsyncSession) -> User:
    """Create test admin"""
    user = User(
        email=f"test_admin_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=get_password_hash("adminpassword"),
        last_name="Админов",
        first_name="Админ",
        middle_name="Админович",
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def auth_headers_student(test_user: User) -> dict:
    from app.core.security import create_access_token
    token = create_access_token(str(test_user.id), additional_claims={"role": test_user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def auth_headers_teacher(test_teacher: User) -> dict:
    from app.core.security import create_access_token
    token = create_access_token(str(test_teacher.id), additional_claims={"role": test_teacher.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def auth_headers_admin(test_admin: User) -> dict:
    from app.core.security import create_access_token
    token = create_access_token(str(test_admin.id), additional_claims={"role": test_admin.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def async_client(client: AsyncClient) -> AsyncClient:
    return client

@pytest.fixture
async def db_session(db: AsyncSession) -> AsyncSession:
    return db

@pytest.fixture
async def admin_user(test_admin: User) -> User:
    return test_admin

@pytest.fixture
async def admin_token(test_admin: User) -> str:
    from app.core.security import create_access_token
    return create_access_token(str(test_admin.id), additional_claims={"role": test_admin.role})

@pytest.fixture
async def teacher_token(test_teacher: User) -> str:
    from app.core.security import create_access_token
    return create_access_token(str(test_teacher.id), additional_claims={"role": test_teacher.role})
