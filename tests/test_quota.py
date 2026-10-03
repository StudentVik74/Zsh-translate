"""Тесты для check_quota.

Проверяет ответы MyMemory API:
- quotaFinished: true  → True
- responseStatus: 429  → True
- успешный ответ       → False
- ошибка сети/JSON     → None
- параметр de (email) передаётся, только если задан.
"""
from unittest.mock import MagicMock

import pytest
import requests

from utils import translate as mt


# ─── Успешные и явные ответы ──────────────────────────────────────

def test_quota_finished_true(mock_requests):
	mock_requests.return_value.json.return_value = {
		"quotaFinished": True,
		"responseStatus": 200,
	}
	assert mt.check_quota() is True


def test_quota_status_429(mock_requests):
	mock_requests.return_value.json.return_value = {
		"quotaFinished": False,
		"responseStatus": 429,
	}
	assert mt.check_quota() is True


def test_quota_ok(mock_requests):
	mock_requests.return_value.json.return_value = {
		"quotaFinished": False,
		"responseStatus": 200,
	}
	assert mt.check_quota() is False


def test_quota_no_status_field(mock_requests):
	"""Если responseStatus отсутствует и quotaFinished false — считаем, что квота есть."""
	mock_requests.return_value.json.return_value = {"quotaFinished": False}
	assert mt.check_quota() is False


# ─── Ошибки → None ────────────────────────────────────────────────

def test_quota_connection_error(mock_requests):
	mock_requests.side_effect = requests.ConnectionError("no network")
	assert mt.check_quota() is None


def test_quota_timeout(mock_requests):
	mock_requests.side_effect = requests.Timeout("timeout")
	assert mt.check_quota() is None


def test_quota_broken_json(mock_requests):
	mock_requests.return_value.json.side_effect = ValueError("not json")
	assert mt.check_quota() is None


# ─── Email (параметр de) ─────────────────────────────────────────

def test_quota_without_email(mock_requests):
	"""Без email параметр de не передаётся."""
	mock_requests.return_value.json.return_value = {"responseStatus": 200}
	mt.check_quota()
	params = mock_requests.call_args.kwargs["params"]
	assert "de" not in params


def test_quota_with_email(mock_requests, monkeypatch):
	"""С email параметр de передаётся."""
	monkeypatch.setattr(mt, "MYMEMORY_EMAIL", "test@example.com")
	mock_requests.return_value.json.return_value = {"responseStatus": 200}
	mt.check_quota()
	params = mock_requests.call_args.kwargs["params"]
	assert params["de"] == "test@example.com"


# ─── Корректность запроса ────────────────────────────────────────

def test_quota_url_and_timeout(mock_requests):
	"""Запрос идёт на LT_URL с timeout=10."""
	mock_requests.return_value.json.return_value = {"responseStatus": 200}
	mt.check_quota()
	call = mock_requests.call_args
	assert call.args[0] == mt.LT_URL
	assert call.kwargs["timeout"] == 10


def test_quota_langpair(mock_requests):
	"""langpair=en|ru для проверки."""
	mock_requests.return_value.json.return_value = {"responseStatus": 200}
	mt.check_quota()
	params = mock_requests.call_args.kwargs["params"]
	assert params["langpair"] == "en|ru"