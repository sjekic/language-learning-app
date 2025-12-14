import importlib.util
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure env vars needed by service modules exist
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("FIREBASE_SERVICE_ACCOUNT_KEY", '{"type": "service_account"}')
os.environ.setdefault("AUTH_SERVICE_URL", "http://auth-service")
os.environ.setdefault("DEV_MODE", "true")

# Provide lightweight stand-ins for optional dependencies
if "asyncpg" not in sys.modules:
    sys.modules["asyncpg"] = MagicMock()
    sys.modules["asyncpg"].create_pool = AsyncMock()

if "firebase_admin" not in sys.modules:
    fb_mock = MagicMock()
    sys.modules["firebase_admin"] = fb_mock
    sys.modules["firebase_admin.credentials"] = MagicMock()
    sys.modules["firebase_admin.auth"] = MagicMock()

if "dotenv" not in sys.modules:
    dotenv_mock = MagicMock()
    dotenv_mock.load_dotenv = MagicMock()
    sys.modules["dotenv"] = dotenv_mock


class FakeAsyncpgConnection:
    """In-memory asyncpg-like connection shared by services."""

    def __init__(self) -> None:
        self.users: Dict[int, Dict] = {}
        self.books: Dict[int, Dict] = {}
        self.user_books: set[tuple[int, int]] = set()
        self.vocabulary: Dict[int, Dict] = {}
        self._ids = {"users": 1, "books": 1, "vocab": 1}

    # Internal helpers
    def _get_user_by_uid(self, firebase_uid: str) -> Optional[Dict]:
        return next((u for u in self.users.values() if u["firebase_uid"] == firebase_uid), None)

    def _create_user(self, firebase_uid: str, email: str, display_name: str) -> Dict:
        now = datetime.utcnow()
        user_id = self._ids["users"]
        self._ids["users"] += 1
        user = {
            "id": user_id,
            "firebase_uid": firebase_uid,
            "email": email,
            "display_name": display_name,
            "created_at": now,
            "updated_at": now,
        }
        self.users[user_id] = user
        return user

    def _create_book(self, language_code: str, genre: str) -> int:
        now = datetime.utcnow()
        book_id = self._ids["books"]
        self._ids["books"] += 1
        self.books[book_id] = {
            "id": book_id,
            "title": "Vocabulary",
            "description": "Auto-created vocab book",
            "text_blob_url": "about:blank",
            "language_code": language_code,
            "genre": genre,
            "is_pro_book": False,
            "created_at": now,
            "updated_at": now,
        }
        return book_id

    def _find_vocab(self, user_id: int, book_id: int, language_code: str, word: str) -> Optional[Dict]:
        return next(
            (
                v
                for v in self.vocabulary.values()
                if v["user_id"] == user_id
                and v["book_id"] == book_id
                and v["language_code"] == language_code
                and v["word"] == word
            ),
            None,
        )

    # asyncpg-like methods
    async def fetchrow(self, query: str, *params):
        q = query.lower()

        if "update users" in q and "returning" in q:
            # Update user display name
            display_name = params[0]
            user_id = int(params[-1])
            user = self.users.get(user_id)
            if not user:
                user = self._create_user(f"uid-{user_id}", f"user{user_id}@example.com", display_name)
            user["display_name"] = display_name
            user["updated_at"] = datetime.utcnow()
            return dict(user)

        if "from users" in q and "firebase_uid" in q:
            user = self._get_user_by_uid(params[0])
            return dict(user) if user else None

        if q.strip().startswith("insert into users"):
            firebase_uid, email, display_name = params
            existing = self._get_user_by_uid(firebase_uid)
            if existing:
                return dict(existing)
            return dict(self._create_user(firebase_uid, email, display_name))

        if "from users" in q and "where id" in q:
            user = self.users.get(int(params[0]))
            return dict(user) if user else None

        if "from vocabulary" in q and "hover_count" in q:
            vocab = self._find_vocab(int(params[0]), int(params[1]), params[2], params[3])
            return dict(vocab) if vocab else None

        if q.strip().startswith("update vocabulary"):
            translation, vocab_id = params
            vocab = self.vocabulary.get(int(vocab_id))
            if vocab:
                vocab["translation"] = translation
                vocab["hover_count"] += 1
                vocab["last_seen_at"] = datetime.utcnow()
                vocab["updated_at"] = datetime.utcnow()
                return dict(vocab)
            return None

        if q.strip().startswith("insert into vocabulary"):
            user_id, book_id, language_code, word, translation = params
            vocab_id = self._ids["vocab"]
            self._ids["vocab"] += 1
            now = datetime.utcnow()
            vocab = {
                "id": vocab_id,
                "user_id": int(user_id),
                "book_id": int(book_id),
                "language_code": language_code,
                "word": word,
                "translation": translation,
                "hover_count": 1,
                "last_seen_at": now,
                "created_at": now,
                "updated_at": now,
            }
            self.vocabulary[vocab_id] = vocab
            return dict(vocab)

        return None

    async def fetch(self, query: str, *params):
        q = query.lower()

        if "group by language_code" in q:
            user_id = int(params[0])
            aggregates: Dict[str, int] = {}
            for v in self.vocabulary.values():
                if v["user_id"] != user_id:
                    continue
                aggregates[v["language_code"]] = aggregates.get(v["language_code"], 0) + 1
            return [{"language_code": lang, "count": count} for lang, count in aggregates.items()]

        if "order by hover_count" in q:
            user_id = int(params[0])
            items = [v for v in self.vocabulary.values() if v["user_id"] == user_id]
            items.sort(key=lambda v: (-v["hover_count"], -v["created_at"].timestamp()))
            return [dict(v) for v in items[:10]]

        if "from vocabulary" in q:
            user_id = int(params[0])
            limit = params[-2]
            offset = params[-1]
            book_id = None
            language_code = None
            idx = 1
            if "and book_id" in q:
                book_id = int(params[idx])
                idx += 1
            if "and language_code" in q:
                language_code = params[idx]

            items = [v for v in self.vocabulary.values() if v["user_id"] == user_id]
            if book_id is not None:
                items = [v for v in items if v["book_id"] == book_id]
            if language_code:
                items = [v for v in items if v["language_code"] == language_code]

            items.sort(key=lambda v: (v.get("last_seen_at") or v["created_at"]), reverse=True)
            window = items[offset : offset + limit]
            return [dict(v) for v in window]

        return []

    async def fetchval(self, query: str, *params):
        q = query.lower()

        if "join user_books" in q and "from books" in q:
            user_id = int(params[0])
            language_code = params[1]
            for bid in (b for b in self.books if (user_id, b) in self.user_books):
                book = self.books[bid]
                if book["genre"] == "vocabulary" and book["language_code"] == language_code:
                    return bid
            return None

        if q.strip().startswith("insert into books"):
            _, _, _, language_code, genre = params
            return self._create_book(language_code, genre)

        if "count" in q and "from vocabulary" in q:
            user_id = int(params[0])
            return len([v for v in self.vocabulary.values() if v["user_id"] == user_id])

        return None

    async def execute(self, query: str, *params):
        q = query.lower()

        if "insert into user_books" in q:
            self.user_books.add((int(params[0]), int(params[1])))
            return "INSERT 0 1"

        if "delete from vocabulary" in q:
            vocab_id, user_id = params
            vocab = self.vocabulary.get(int(vocab_id))
            if not vocab or vocab["user_id"] != int(user_id):
                return "DELETE 0"
            del self.vocabulary[int(vocab_id)]
            return "DELETE 1"

        return "OK"


def _load_service_module(service_dir: Path, prefix: str):
    """Load database + main with unique module names to avoid collisions."""
    sys.path.insert(0, str(service_dir))

    db_spec = importlib.util.spec_from_file_location(f"{prefix}_database", service_dir / "database.py")
    db_module = importlib.util.module_from_spec(db_spec)
    sys.modules["database"] = db_module
    sys.modules[f"{prefix}_database"] = db_module
    db_spec.loader.exec_module(db_module)

    main_spec = importlib.util.spec_from_file_location(f"{prefix}_main", service_dir / "main.py")
    main_module = importlib.util.module_from_spec(main_spec)
    sys.modules[f"{prefix}_main"] = main_module
    main_spec.loader.exec_module(main_module)
    return main_module


@pytest.fixture(scope="session")
def service_apps():
    base = Path(__file__).resolve().parent.parent / "services"
    auth_main = _load_service_module(base / "auth-service", "integration_auth")
    user_main = _load_service_module(base / "user-service", "integration_user")
    translation_main = _load_service_module(base / "translation-service", "integration_translation")
    return auth_main, user_main, translation_main


@pytest.fixture
def integration_apps(monkeypatch, service_apps):
    auth_main, user_main, translation_main = service_apps
    fake_db = FakeAsyncpgConnection()

    async def _get_db():
        return fake_db

    for module in (auth_main, user_main, translation_main):
        monkeypatch.setattr(module, "get_db_connection", AsyncMock(side_effect=_get_db))
        monkeypatch.setattr(module, "close_db_connection", AsyncMock())

    def _fake_verify(token: str):
        return {
            "uid": token,
            "email": f"{token}@example.com",
            "name": "Integration User",
            "email_verified": True,
        }

    monkeypatch.setattr(auth_main, "verify_firebase_token", _fake_verify)
    monkeypatch.setattr(auth_main, "initialize_firebase", lambda: True)
    monkeypatch.setattr(auth_main, "get_firebase_user", lambda uid: {"uid": uid, "email": f"{uid}@example.com"})

    # Load firebase_config module for coverage-friendly access
    auth_base = Path(__file__).resolve().parent.parent / "services" / "auth-service"
    fb_spec = importlib.util.spec_from_file_location("integration_auth_firebase", auth_base / "firebase_config.py")
    fb_module = importlib.util.module_from_spec(fb_spec)
    sys.modules["integration_auth_firebase"] = fb_module
    fb_spec.loader.exec_module(fb_module)
    auth_main.firebase_config = fb_module

    transport = httpx.ASGITransport(app=auth_main.app)
    real_async_client = httpx.AsyncClient

    def _auth_client_factory(*args, **kwargs):
        kwargs.setdefault("transport", transport)
        kwargs.setdefault("base_url", "http://auth-service")
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(user_main.httpx, "AsyncClient", _auth_client_factory)
    monkeypatch.setattr(translation_main.httpx, "AsyncClient", _auth_client_factory)
    user_main.AUTH_SERVICE_URL = "http://auth-service"
    translation_main.AUTH_SERVICE_URL = "http://auth-service"

    return {
        "auth": auth_main.app,
        "user": user_main.app,
        "translation": translation_main.app,
        "db": fake_db,
        "modules": {"auth": auth_main, "user": user_main, "translation": translation_main},
    }


@pytest.mark.asyncio
async def test_auth_translation_user_flow(integration_apps):
    apps = integration_apps
    token = "integration-token"
    headers = {"Authorization": f"Bearer {token}"}

    # Auth: create/sync user
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=apps["auth"]),
        base_url="http://auth-service",
    ) as client:
        root_resp = await client.get("/")
        assert root_resp.status_code == 200

        auth_resp = await client.post("/api/auth/verify", json={"id_token": token, "display_name": "Integration User"})
        assert auth_resp.status_code == 200
        user_id = auth_resp.json()["user"]["id"]

    # Translation: save vocabulary, list, stats
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=apps["translation"]),
        base_url="http://translation-service",
    ) as client:
        save_resp = await client.post(
            "/api/vocabulary",
            json={"word": "hola", "translation": "hello", "language_code": "es", "book_id": None},
            headers=headers,
        )
        assert save_resp.status_code == 201
        vocab_payload = save_resp.json()

        list_resp = await client.get("/api/vocabulary", headers=headers)
        assert list_resp.status_code == 200
        vocab_list = list_resp.json()
        assert len(vocab_list) == 1
        assert vocab_list[0]["book_id"] == vocab_payload["book_id"]

        stats_resp = await client.get("/api/vocabulary/stats", headers=headers)
        assert stats_resp.status_code == 200
        assert stats_resp.json()["total_words"] == 1

    # User: fetch profile (depends on auth + DB wiring)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=apps["user"]),
        base_url="http://user-service",
    ) as client:
        root_resp = await client.get("/")
        assert root_resp.status_code == 200

        profile_resp = await client.get("/api/users/me", headers=headers)
        assert profile_resp.status_code == 200
        profile = profile_resp.json()
        assert profile["id"] == user_id
        assert profile["email"].startswith(token)

    # Shared fake DB state sanity check
    assert len(apps["db"].books) == 1
    assert (user_id, vocab_payload["book_id"]) in apps["db"].user_books


@pytest.mark.asyncio
async def test_auth_token_verify_and_firebase_user(integration_apps):
    apps = integration_apps
    token = "integration-token-2"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=apps["auth"]),
        base_url="http://auth-service",
    ) as client:
        # Valid token verify
        verify_resp = await client.post("/api/auth/token/verify", headers=headers)
        assert verify_resp.status_code == 200
        # Invalid header format
        bad_resp = await client.post("/api/auth/token/verify", headers={"Authorization": "Token nope"})
        assert bad_resp.status_code == 401

        # Firebase user info (self access)
        firebase_resp = await client.get(f"/api/auth/firebase-user/{token}", headers=headers)
        assert firebase_resp.status_code == 200
        assert firebase_resp.json()["uid"] == token

        login_legacy = await client.post("/api/auth/login")
        assert login_legacy.status_code == 410
        signup_legacy = await client.post("/api/auth/signup")
        assert signup_legacy.status_code == 410


@pytest.mark.asyncio
async def test_auth_verify_header_errors(integration_apps, monkeypatch):
    apps = integration_apps
    auth_module = integration_apps["modules"]["auth"]

    # Invalid format
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=apps["auth"]),
        base_url="http://auth-service",
    ) as client:
        bad_header = await client.post("/api/auth/token/verify", headers={"Authorization": "Token nope"})
        assert bad_header.status_code == 401

    # Missing email in firebase data -> 400
    def _bad_verify(token: str):
        return {"uid": token}

    auth_module.verify_firebase_token = _bad_verify
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=apps["auth"]),
        base_url="http://auth-service",
    ) as client:
        missing_email = await client.post("/api/auth/token/verify", headers={"Authorization": "Bearer tok"})
        assert missing_email.status_code == 400


@pytest.mark.asyncio
async def test_user_profile_success_and_not_found(integration_apps):
    apps = integration_apps
    token = "integration-token-3"
    headers = {"Authorization": f"Bearer {token}"}

    # Seed user directly
    if not apps["db"].users:
        apps["db"]._create_user(token, f"{token}@example.com", "Profile User")

    user_module = integration_apps["modules"]["user"]
    async def _mock_verify():
        return {"user": {"id": next(iter(apps["db"].users.keys()), 1)}}
    user_module.app.dependency_overrides[user_module.verify_token] = _mock_verify
    user_module.get_db_connection = AsyncMock(return_value=apps["db"])

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=apps["user"]),
        base_url="http://user-service",
    ) as client:
        profile_resp = await client.get("/api/users/me", headers=headers)
        assert profile_resp.status_code == 200
        assert profile_resp.json()["email"].endswith("@example.com")

        apps["db"].users.clear()
        not_found_resp = await client.get("/api/users/me", headers=headers)
        assert not_found_resp.status_code == 404


@pytest.mark.asyncio
async def test_translation_vocabulary_filters_and_delete(integration_apps):
    apps = integration_apps
    modules = integration_apps["modules"]
    token = "integration-token-4"
    headers = {"Authorization": f"Bearer {token}"}

    # Seed user
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=apps["auth"]),
        base_url="http://auth-service",
    ) as client:
        await client.post("/api/auth/verify", json={"id_token": token, "display_name": "Integration User"})
    # Ensure user record exists in fake DB with consistent id
    if not apps["db"].users:
        apps["db"]._create_user(token, f"{token}@example.com", "Integration User")

    # Override auth dependency to avoid outbound calls
    translation_module = modules["translation"]
    async def _mock_verify():
        return {"user": {"id": next(iter(apps["db"].users.keys()), 1)}}
    translation_module.app.dependency_overrides[translation_module.verify_token] = _mock_verify
    translation_module.get_db_connection = AsyncMock(return_value=apps["db"])

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=apps["translation"]),
        base_url="http://translation-service",
    ) as client:
        root_resp = await client.get("/")
        assert root_resp.status_code == 200

        save_resp = await client.post(
            "/api/vocabulary",
            json={"word": "hola", "translation": "hello", "language_code": "es", "book_id": None},
            headers=headers,
        )
        assert save_resp.status_code == 201
        vocab_payload = save_resp.json()
        book_id = vocab_payload.get("book_id") or next(iter(apps["db"].books.keys()), None)

        filtered_resp = await client.get(
            f"/api/vocabulary?book_id={book_id}&language=spanish&limit=10&offset=0",
            headers=headers,
        )
        assert filtered_resp.status_code == 200

        delete_resp = await client.delete(f"/api/vocabulary/{vocab_payload['id']}", headers=headers)
        assert delete_resp.status_code == 200

        missing_resp = await client.delete(f"/api/vocabulary/{vocab_payload['id']}", headers=headers)
        assert missing_resp.status_code == 404

        stats_resp = await client.get("/api/vocabulary/stats", headers=headers)
        assert stats_resp.status_code == 200
        assert stats_resp.json()["total_words"] == 0

        bad_header = await client.post("/api/vocabulary", json={}, headers={"Authorization": "Token nope"})
        assert bad_header.status_code in (401, 422)


@pytest.mark.asyncio
async def test_user_update_display_name(integration_apps):
    apps = integration_apps
    token = "integration-token-5"
    headers = {"Authorization": f"Bearer {token}"}

    # Seed user directly
    user_id = apps["db"]._create_user(token, f"{token}@example.com", "Old Name")["id"]

    user_module = integration_apps["modules"]["user"]

    async def _mock_verify():
        return {"user": {"id": user_id}}

    user_module.app.dependency_overrides[user_module.verify_token] = _mock_verify
    user_module.get_db_connection = AsyncMock(return_value=apps["db"])

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=apps["user"]),
        base_url="http://user-service",
    ) as client:
        update_resp = await client.put("/api/users/me", json={"display_name": "New Name"}, headers=headers)
        assert update_resp.status_code == 200
        assert update_resp.json()["display_name"] == "New Name"

        no_fields_resp = await client.put("/api/users/me", json={}, headers=headers)
        assert no_fields_resp.status_code == 400


@pytest.mark.asyncio
async def test_translation_translate_success(integration_apps):
    apps = integration_apps
    modules = integration_apps["modules"]
    token = "integration-token-6"
    headers = {"Authorization": f"Bearer {token}"}

    # Seed user
    apps["db"]._create_user(token, f"{token}@example.com", "Translation User")

    translation_module = modules["translation"]

    async def _mock_verify():
        return {"user": {"id": next(iter(apps["db"].users.keys()), 1)}}

    translation_module.app.dependency_overrides[translation_module.verify_token] = _mock_verify
    translation_module.get_db_connection = AsyncMock(return_value=apps["db"])

    sample_payload = [
        {
            "translations": [
                {"text": "hello", "examples": [{"src": "Hola", "dst": "Hello"}]},
                {"text": "hi"},
            ]
        }
    ]
    fake_httpx_response = httpx.Response(status_code=200, json=sample_payload)

    def _fake_async_client(*args, **kwargs):
        class _AClient:
            async def __aenter__(self_inner):
                return self_inner

            async def __aexit__(self_inner, exc_type, exc_val, exc_tb):
                return False

            async def get(self_inner, *a, **kw):
                return fake_httpx_response

        return _AClient()

    translation_module.translation_cache.clear()

    with patch.object(translation_module.httpx, "AsyncClient", _fake_async_client):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=apps["translation"]),
            base_url="http://translation-service",
        ) as client:
            resp = await client.get("/api/translate?query=hola&src=es&dst=en", headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            if isinstance(data, dict):
                assert data["translations"][0] == "hello"
            else:
                assert data[0]["translations"][0]["text"] == "hello"


@pytest.mark.asyncio
async def test_translation_translate_no_matches(integration_apps):
    apps = integration_apps
    modules = integration_apps["modules"]
    token = "integration-token-7"
    headers = {"Authorization": f"Bearer {token}"}

    translation_module = modules["translation"]

    async def _mock_verify():
        return {"user": {"id": apps["db"]._create_user(token, f"{token}@example.com", "User")["id"]}}

    translation_module.app.dependency_overrides[translation_module.verify_token] = _mock_verify
    translation_module.get_db_connection = AsyncMock(return_value=apps["db"])
    translation_module.translation_cache.clear()

    def _fake_async_client(*args, **kwargs):
        class _AClient:
            async def __aenter__(self_inner):
                return self_inner

            async def __aexit__(self_inner, exc_type, exc_val, exc_tb):
                return False

            async def get(self_inner, *a, **kw):
                return httpx.Response(status_code=200, json=[])

        return _AClient()

    with patch.object(translation_module.httpx, "AsyncClient", _fake_async_client):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=apps["translation"]),
            base_url="http://translation-service",
        ) as client:
            resp = await client.get("/api/translate?query=zzz&src=es&dst=en", headers=headers)
            assert resp.status_code == 200
            data = resp.json()
        if isinstance(data, dict):
            assert "Translation not found" in data["translations"][0]
        else:
            assert data == []


@pytest.mark.asyncio
async def test_translation_vocabulary_book_creation(integration_apps):
    modules = integration_apps["modules"]
    translation_module = modules["translation"]
    fake_db = integration_apps["db"]
    user_id = fake_db._create_user("vocab-user", "vocab@example.com", "Vocab User")["id"]

    translation_module.get_db_connection = AsyncMock(return_value=fake_db)
    # First call should create
    book_id = await translation_module.ensure_vocabulary_book_for_user(user_id=user_id, language_code="es")
    # Second call should reuse
    book_id_2 = await translation_module.ensure_vocabulary_book_for_user(user_id=user_id, language_code="es")
    assert book_id == book_id_2


def test_firebase_config_helpers(integration_apps, monkeypatch):
    base = Path(__file__).resolve().parent.parent / "services" / "auth-service"
    spec = importlib.util.spec_from_file_location("integration_auth_firebase", base / "firebase_config.py")
    firebase_config = importlib.util.module_from_spec(spec)
    sys.modules["integration_auth_firebase"] = firebase_config
    spec.loader.exec_module(firebase_config)

    firebase_config._firebase_app = None
    firebase_config.firebase_admin.credentials = MagicMock()
    firebase_config.firebase_admin.credentials.Certificate = MagicMock(return_value="cred")
    firebase_config.firebase_admin.initialize_app = MagicMock(return_value="app")
    firebase_config.auth.verify_id_token = MagicMock(return_value={"uid": "x", "email": "x@example.com"})
    firebase_config.auth.get_user = MagicMock()
    firebase_config.auth.create_custom_token = MagicMock(return_value=b"tok123")

    # initialize_firebase with env key
    os.environ["FIREBASE_SERVICE_ACCOUNT_KEY"] = '{"type": "service_account"}'
    app_instance = firebase_config.initialize_firebase()
    assert app_instance == "app"

    # verify token success
    assert firebase_config.verify_firebase_token("tok")["uid"] == "x"

    # verify token invalid
    firebase_config.auth.verify_id_token.side_effect = ValueError("Invalid token")
    with pytest.raises(ValueError):
        firebase_config.verify_firebase_token("bad")

    # initialize_firebase with path
    firebase_config._firebase_app = None
    os.environ.pop("FIREBASE_SERVICE_ACCOUNT_KEY", None)
    os.environ["FIREBASE_SERVICE_ACCOUNT_PATH"] = "/tmp/fake.json"
    firebase_config.credentials.Certificate = MagicMock(return_value="cred2")
    firebase_config.firebase_admin.initialize_app = MagicMock(return_value="app2")
    assert firebase_config.initialize_firebase() == "app2"

    # initialize_firebase no creds
    firebase_config._firebase_app = None
    os.environ.pop("FIREBASE_SERVICE_ACCOUNT_PATH", None)
    os.environ.pop("FIREBASE_SERVICE_ACCOUNT_KEY", None)
    assert firebase_config.initialize_firebase() is None

    # get user success/failure
    user_mock = MagicMock()
    user_mock.uid = "u1"
    user_mock.email = "u@example.com"
    user_mock.email_verified = True
    user_mock.display_name = "User"
    user_mock.photo_url = None
    user_mock.disabled = False
    firebase_config.auth.verify_id_token.side_effect = None
    firebase_config.auth.get_user.return_value = user_mock
    user_info = firebase_config.get_firebase_user("u1")
    assert user_info["uid"] == "u1"

    firebase_config.auth.get_user.side_effect = Exception("not found")
    with pytest.raises(ValueError):
        firebase_config.get_firebase_user("missing")

    # custom token success/failure
    assert firebase_config.create_custom_token("u1") == "tok123"
    firebase_config.auth.create_custom_token.side_effect = Exception("fail")
    with pytest.raises(ValueError):
        firebase_config.create_custom_token("u1")


# -------------------------------------------------
# Database module coverage (auth/translation/user)
# -------------------------------------------------
def _load_db_module(path, name):
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
async def test_database_get_connection_and_close(module_name, monkeypatch):
    base_path = Path(__file__).resolve().parent.parent / "services"
    file_map = {
        "auth_db": base_path / "auth-service" / "database.py",
        "translation_db": base_path / "translation-service" / "database.py",
        "user_db": base_path / "user-service" / "database.py",
    }

    sys.modules["asyncpg"] = MagicMock()
    sys.modules["asyncpg"].create_pool = AsyncMock(return_value=AsyncMock())

    db_module = _load_db_module(file_map[module_name], module_name)

    with pytest.raises(ValueError):
        os.environ.pop("DATABASE_URL", None)
        db_module.pool = None
        await db_module.get_db_connection()

    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test"
    db_module.pool = None
    pool = await db_module.get_db_connection()
    assert pool is not None

    reused = await db_module.get_db_connection()
    assert reused is pool

    await db_module.close_db_connection()
