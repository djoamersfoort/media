import asyncio
from typing import AsyncGenerator
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.db import crud
from app.db.database import Base, get_db
from app.main import app

# Use a separate SQLite in-memory database for tests
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def mock_oidc():
    from app import main
    main.get_openid_configuration = MagicMock(return_value={
        "jwks_uri": "http://test/jwks",
        "id_token_signing_alg_values_supported": ["RS256"]
    })
    main.get_jwks_client = MagicMock()
    yield

@pytest.fixture(autouse=True)
def mock_signing():
    mock_signer = MagicMock()
    mock_signer.sign.return_value = b"mock_signature"
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = True
    
    # Patch lru_cache decorated functions
    crud.get_signer = MagicMock(return_value=mock_signer)
    crud.get_verifier = MagicMock(return_value=mock_verifier)
    yield

@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture
def mock_user():
    from app.db.schemas import User
    return User(id="test_user", admin=True)

@pytest.fixture
def mock_regular_user():
    from app.db.schemas import User
    return User(id="regular_user", admin=False)

@pytest_asyncio.fixture(scope="function")
async def admin_client(client: AsyncClient, mock_user) -> AsyncGenerator[AsyncClient, None]:
    from app.main import get_user_dep
    app.dependency_overrides[get_user_dep] = lambda: mock_user
    yield client
    app.dependency_overrides.pop(get_user_dep, None)

@pytest_asyncio.fixture(scope="function")
async def regular_client(client: AsyncClient, mock_regular_user) -> AsyncGenerator[AsyncClient, None]:
    from app.main import get_user_dep
    app.dependency_overrides[get_user_dep] = lambda: mock_regular_user
    yield client
    app.dependency_overrides.pop(get_user_dep, None)
