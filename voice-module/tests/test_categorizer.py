import sys
import os
import pytest
from unittest.mock import patch

# Ensure project root is on sys.path so tests can import local modules
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import categorizer


def test_keyword_revenue():
    cat, score = categorizer.get_category_from_rules("sold 10 cakes for 500")
    assert cat == "Revenue"


def test_keyword_inventory():
    cat, score = categorizer.get_category_from_rules("bought flour and oil")
    assert cat == "Inventory"


def test_keyword_utilities():
    cat, score = categorizer.get_category_from_rules("paid electricity bill")
    assert cat == "Utilities"


def test_keyword_personal():
    cat, score = categorizer.get_category_from_rules("bought shoes for myself")
    assert cat == "Personal"


def test_keyword_rent():
    cat, score = categorizer.get_category_from_rules("paid shop rent 5000")
    assert cat == "Rent"


def test_keyword_transport():
    cat, score = categorizer.get_category_from_rules("took uber to market")
    assert cat == "Transport"


def test_keyword_food():
    cat, score = categorizer.get_category_from_rules("had lunch at hotel")
    assert cat == "Food"


@patch('categorizer.get_category_from_gemini')
def test_fallback_other(mock_gemini):
    mock_gemini.return_value = "Other"
    cat, score = categorizer.get_category_from_rules("xyz abc random 123")
    assert cat == "Other"


def test_confidence_high():
    cat, score = categorizer.get_category_from_rules("sold 2 items")
    assert score >= 0.85


@patch('categorizer.get_category_from_gemini')
def test_confidence_fallback(mock_gemini):
    mock_gemini.return_value = "Other"
    cat, score = categorizer.get_category_from_rules("no match text qwerty")
    assert score <= 0.75


def test_apply_categorization_list():
    txs = [
        {"description": "sold apples", "amount": 100},
        {"description": "bought flour", "amount": 200},
        {"description": "had lunch", "amount": 50},
    ]
    res = categorizer.apply_categorization(txs)
    for r in res:
        assert r.get('category') is not None


def test_apply_categorization_returns_list():
    txs = [{"description": "sold apples", "amount": 100}]
    res = categorizer.apply_categorization(txs)
    assert isinstance(res, list)
