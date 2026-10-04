"""
Общие фикстуры для тестов mymemory_translator.

Фикстуры:
- reset_flags   — сброс глобальных флагов между тестами (autouse)
- temp_cache    — подмена CACHE_FILE на временный путь
- mock_requests — мок requests.get для изоляции от сети
"""
import sys
from pathlib import Path

import pytest

# Гарантируем, что корень проекта в sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from utils import translate as mt


@pytest.fixture(autouse=True)
def reset_flags(monkeypatch):
	"""Сбросить глобальные флаги перед каждым тестом."""
	monkeypatch.setattr(mt, "_api_warned", False)
	monkeypatch.setattr(mt, "_cache_warned", False)
	yield


@pytest.fixture
def temp_cache(tmp_path, monkeypatch):
	"""Подменить CACHE_FILE на временный файл в tmp_path."""
	fake = tmp_path / "translate_ru.json"
	monkeypatch.setattr(mt, "CACHE_FILE", str(fake))
	return fake


@pytest.fixture
def mock_requests(mocker):
	"""Мок requests.get.

	Использование:
		mock_requests.return_value.json.return_value = {...}
	"""
	return mocker.patch("utils/translate.requests.get")
