import os
import sys
import importlib.util
from unittest.mock import AsyncMock, MagicMock

import pytest


def load_db_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name",
    [
        "auth_db",
        "translation_db",
        "user_db",
    ],
)
async def test_database_get_connection_and_close(module_name, tmp_path, monkeypatch):
    base = (
        (tmp_path / "services")  # placeholder, we override spec path below
    )
    base_path = os.path.join(os.path.dirname(__file__), "..", "services")
    file_map = {
        "auth_db": os.path.join(base_path, "auth-service", "database.py"),
        "translation_db": os.path.join(base_path, "translation-service", "database.py"),
        "user_db": os.path.join(base_path, "user-service", "database.py"),
    }

    # Provide asyncpg stub before loading
    sys.modules["asyncpg"] = MagicMock()
    sys.modules["asyncpg"].create_pool = AsyncMock(return_value=AsyncMock())

    db_module = load_db_module(file_map[module_name], module_name)

    with pytest.raises(ValueError):
        os.environ.pop("DATABASE_URL", None)
        db_module.pool = None
        await db_module.get_db_connection()

    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test"
    db_module.pool = None
    pool = await db_module.get_db_connection()
    assert pool is not None

    # Reuse existing pool branch
    reused = await db_module.get_db_connection()
    assert reused is pool

    await db_module.close_db_connection()
