import os
import sys
from unittest.mock import Mock

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import server


@pytest.fixture
def client():
    server.app.config["TESTING"] = True
    return server.app.test_client()


def test_save_transactions_rejects_invalid_amount(client, monkeypatch):
    mock_supabase = Mock()
    monkeypatch.setattr(server, "supabase", mock_supabase)

    response = client.post(
        "/save-transactions",
        json={
            "transactions": [
                {
                    "description": "test",
                    "amount": "hello",
                    "category": "Food",
                    "confidence_score": 0.8
                }
            ]
        }
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert "Invalid amount" in response.get_json()["error"]
    mock_supabase.table.assert_not_called()


def test_save_transactions_rejects_invalid_category(client, monkeypatch):
    mock_supabase = Mock()
    monkeypatch.setattr(server, "supabase", mock_supabase)

    response = client.post(
        "/save-transactions",
        json={
            "transactions": [
                {
                    "description": "test",
                    "amount": 100,
                    "category": "InvalidCategory",
                    "confidence_score": 0.8
                }
            ]
        }
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert "Invalid category" in response.get_json()["error"]
    mock_supabase.table.assert_not_called()


def test_save_transactions_rejects_invalid_confidence(client, monkeypatch):
    mock_supabase = Mock()
    monkeypatch.setattr(server, "supabase", mock_supabase)

    response = client.post(
        "/save-transactions",
        json={
            "transactions": [
                {
                    "description": "test",
                    "amount": 100,
                    "category": "Food",
                    "confidence_score": 1.5
                }
            ]
        }
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert "Invalid confidence_score" in response.get_json()["error"]
    mock_supabase.table.assert_not_called()
