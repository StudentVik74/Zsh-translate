"""Тесты для lt_translate.

Проверяет основной переводчик:
- успешный ответ → (перевод, True)
- HTTP 500/429 → (оригинал, False)
- responseStatus != 200 в JSON → (оригинал, False)
- битый JSON, KeyError, ошибки сети → (оригинал, False)
- notify_first_failure вызывается один раз
- корректность параметров запроса (q, langpair, timeout, de)
- параметр de передаётся только с email.
"""
import pytest
import requests

from utils import mymemory_translator as mt


# ─── Успешный перевод ─────────────────────────────────────────────

def test_translate_success(mock_requests):
	mock_requests.return_value.json.return_value = {
		"responseData": {"translatedText": "привет"},
		"responseStatus": 200,
	}
	text, ok = mt.lt_translate("hello")
	assert text == "привет"
	assert ok is True


def test_translate_success_tuple_type(mock_requests):
	"""Возврат — именно кортеж из двух элементов."""
	mock_requests.return_value.json.return_value = {
		"responseData": {"translatedText": "привет"},
		"responseStatus": 200,
	}
	result = mt.lt_translate("hello")
	assert isinstance(result, tuple)
	assert len(result) == 2


def test_translate_returns_cyrillic(mock_requests):
	mock_requests.return_value.json.return_value = {
		"responseData": {"translatedText": "Привет, мир!"},
		"responseStatus": 200,
	}
	text, ok = mt.lt_translate("Hello, world!")
	assert text == "Привет, мир!"
	assert ok is True


# ─── HTTP-ошибки ──────────────────────────────────────────────────

def test_translate_http_500(mock_requests):
	mock_requests.return_value.raise_for_status.side_effect = requests.HTTPError("500")
	text, ok = mt.lt_translate("hello")
	assert text == "hello"
	assert ok is False


def test_translate_http_429(mock_requests):
	mock_requests.return_value.raise_for_status.side_effect = requests.HTTPError("429")
	text, ok = mt.lt_translate("hello")
	assert text == "hello"
	assert ok is False


# ─── responseStatus в JSON ────────────────────────────────────────

def test_translate_json_status_429(mock_requests):
	mock_requests.return_value.json.return_value = {
		"responseData": {"translatedText": "?"},
		"responseStatus": 429,
		"responseDetails": "quota exceeded",
	}
	text, ok = mt.lt_translate("hello")
	assert text == "hello"
	assert ok is False


def test_translate_json_status_403(mock_requests):
	mock_requests.return_value.json.return_value = {
		"responseStatus": 403,
		"responseDetails": "forbidden",
	}
	text, ok = mt.lt_translate("hello")
	assert text == "hello"
	assert ok is False


# ─── Ошибки данных ────────────────────────────────────────────────

def test_translate_broken_json(mock_requests):
	mock_requests.return_value.json.side_effect = ValueError("not json")
	text, ok = mt.lt_translate("hello")
	assert text == "hello"
	assert ok is False


def test_translate_missing_response_data(mock_requests):
	"""KeyError — нет ключа responseData."""
	mock_requests.return_value.json.return_value = {
		"responseStatus": 200,
		# нет responseData
	}
	text, ok = mt.lt_translate("hello")
	assert text == "hello"
	assert ok is False


def test_translate_missing_translated_text(mock_requests):
	"""KeyError — нет ключа translatedText внутри responseData."""
	mock_requests.return_value.json.return_value = {
		"responseData": {},
		"responseStatus": 200,
	}
	text, ok = mt.lt_translate("hello")
	assert text == "hello"
	assert ok is False


# ─── Ошибки сети ──────────────────────────────────────────────────

def test_translate_connection_error(mock_requests):
	mock_requests.side_effect = requests.ConnectionError("no network")
	text, ok = mt.lt_translate("hello")
	assert text == "hello"
	assert ok is False


def test_translate_timeout(mock_requests):
	mock_requests.side_effect = requests.Timeout("timeout")
	text, ok = mt.lt_translate("hello")
	assert text == "hello"
	assert ok is False


# ─── Параметры запроса ───────────────────────────────────────────

def test_translate_url_and_timeout(mock_requests):
	mock_requests.return_value.json.return_value = {
		"responseData": {"translatedText": "привет"},
		"responseStatus": 200,
	}
	mt.lt_translate("hello")
	call = mock_requests.call_args
	assert call.args[0] == mt.LT_URL
	assert call.kwargs["timeout"] == 30


def test_translate_params_q_and_langpair(mock_requests):
	mock_requests.return_value.json.return_value = {
		"responseData": {"translatedText": "привет"},
		"responseStatus": 200,
	}
	mt.lt_translate("hello", source="en", target="ru")
	params = mock_requests.call_args.kwargs["params"]
	assert params["q"] == "hello"
	assert params["langpair"] == "en|ru"


def test_translate_custom_languages(mock_requests):
	mock_requests.return_value.json.return_value = {
		"responseData": {"translatedText": "bonjour"},
		"responseStatus": 200,
	}
	mt.lt_translate("hello", source="en", target="fr")
	params = mock_requests.call_args.kwargs["params"]
	assert params["langpair"] == "en|fr"


# ─── Email (параметр de) ─────────────────────────────────────────

def test_translate_without_email(mock_requests):
	mock_requests.return_value.json.return_value = {
		"responseData": {"translatedText": "привет"},
		"responseStatus": 200,
	}
	mt.lt_translate("hello")
	params = mock_requests.call_args.kwargs["params"]
	assert "de" not in params


def test_translate_with_email(mock_requests, monkeypatch):
	monkeypatch.setattr(mt, "MYMEMORY_EMAIL", "test@example.com")
	mock_requests.return_value.json.return_value = {
		"responseData": {"translatedText": "привет"},
		"responseStatus": 200,
	}
	mt.lt_translate("hello")
	params = mock_requests.call_args.kwargs["params"]
	assert params["de"] == "test@example.com"


# ─── notify_first_failure ────────────────────────────────────────

def test_failure_prints_warning_once(mock_requests, capsys):
	"""При первой ошибке печатает [warn], при второй — молчит."""
	mock_requests.side_effect = requests.ConnectionError("no network")

	mt.lt_translate("hello")  # первая ошибка
	captured = capsys.readouterr()
	assert "MyMemory недоступен" in captured.err

	mt.lt_translate("world")  # вторая ошибка — не должна печатать
	captured = capsys.readouterr()
	assert "MyMemory недоступен" not in captured.err


def test_failure_quota_finished_message(mock_requests, monkeypatch, capsys):
	"""Если check_quota вернул True — печатает сообщение о квоте."""
	mock_requests.side_effect = requests.ConnectionError("no network")
	monkeypatch.setattr(mt, "check_quota", lambda: True)

	mt.lt_translate("hello")
	captured = capsys.readouterr()
	assert "квота MyMemory исчерпана" in captured.err


def test_failure_quota_ok_message(mock_requests, monkeypatch, capsys):
	"""Если check_quota вернул False — печатает сообщение о сети."""
	mock_requests.side_effect = requests.ConnectionError("no network")
	monkeypatch.setattr(mt, "check_quota", lambda: False)

	mt.lt_translate("hello")
	captured = capsys.readouterr()
	assert "проблема с сетью" in captured.err


def test_failure_quota_unknown_message(mock_requests, monkeypatch, capsys):
	"""Если check_quota вернул None — только базовое сообщение."""
	mock_requests.side_effect = requests.ConnectionError("no network")
	monkeypatch.setattr(mt, "check_quota", lambda: None)

	mt.lt_translate("hello")
	captured = capsys.readouterr()
	assert "MyMemory недоступен" in captured.err
	assert "квота MyMemory исчерпана" not in captured.err
	assert "проблема с сетью" not in captured.err


# ─── Интеграционный тест (реальный API) ──────────────────────────

@pytest.mark.integration
def test_real_api_translate():
	"""Реальный запрос к MyMemory. Тратит квоту.

	Запуск: uv run pytest -m integration
	"""
	text, ok = mt.lt_translate("Hello")
	assert ok is True
	assert len(text) > 0
	assert text != "Hello"