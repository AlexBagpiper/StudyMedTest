"""
Pytest configuration and fixtures
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.user import User
from app.core.security import get_password_hash

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5432/medtest_test"

# Create async test engine
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)

# Create async session maker
TestSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


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
        email="test@example.com",
        password_hash=get_password_hash("testpassword"),
        full_name="Test User",
        role="student",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def test_teacher(db: AsyncSession) -> User:
    """Create test teacher"""
    user = User(
        email="teacher@example.com",
        password_hash=get_password_hash("teacherpassword"),
        full_name="Test Teacher",
        role="teacher",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def test_admin(db: AsyncSession) -> User:
    """Create test admin"""
    user = User(
        email="admin@example.com",
        password_hash=get_password_hash("adminpassword"),
        full_name="Test Admin",
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
def auth_headers_student(test_user: User) -> dict:
    """Get auth headers for student"""
    from app.core.security import create_access_token
    token = create_access_token(str(test_user.id), additional_claims={"role": test_user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_teacher(test_teacher: User) -> dict:
    """Get auth headers for teacher"""
    from app.core.security import create_access_token
    token = create_access_token(str(test_teacher.id), additional_claims={"role": test_teacher.role})
    return {"Authorization": f"Bearer {token}"}

