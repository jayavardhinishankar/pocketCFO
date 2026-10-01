from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routes import transactions


def test_get_transactions_uses_authenticated_user():
    fake_user_id = "test-user-123"

    fake_context = SimpleNamespace(
        user_id=fake_user_id,
        client=SimpleNamespace()
    )

    fake_service = SimpleNamespace(
        get_transactions=AsyncMock(
            return_value=([], 0)
        )
    )

    app.dependency_overrides[
        transactions.get_authenticated_context_dependency
    ] = lambda: fake_context

    app.dependency_overrides[
        transactions.get_transaction_service
    ] = lambda: fake_service

    try:
        client = TestClient(app)

        response = client.get("/transactions")

        assert response.status_code == 200

        fake_service.get_transactions.assert_awaited_once()

        call_kwargs = fake_service.get_transactions.await_args.kwargs

        assert call_kwargs["user_id"] == fake_user_id

    finally:
        app.dependency_overrides.clear()
