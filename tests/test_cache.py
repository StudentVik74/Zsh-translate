"""Тесты для load_cache и save_cache.

Использует фикстуру temp_cache из conftest.py, которая подменяет
CACHE_FILE на временный путь в tmp_path. Реальный ~/.cache не трогается.
"""
import json

import pytest

from utils import mymemory_translator as mt


# ─── load_cache ───────────────────────────────────────────────────

def test_load_cache_no_file(temp_cache):
	"""Файла нет → пустой словарь."""
	assert mt.load_cache() == {}


def test_load_cache_empty_file(temp_cache):
	"""Пустой файл → пустой словарь."""
	temp_cache.write_text("", encoding="utf-8")
	assert mt.load_cache() == {}


def test_load_cache_valid_json(temp_cache):
	"""Валидный JSON → словарь с данными."""
	data = {"hash1": "перевод1", "hash2": "перевод2"}
	temp_cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
	assert mt.load_cache() == data


def test_load_cache_broken_json(temp_cache):
	"""Битый JSON → пустой словарь."""
	temp_cache.write_text("{not valid json", encoding="utf-8")
	assert mt.load_cache() == {}


def test_load_cache_json_array(temp_cache):
	"""JSON-массив (не словарь) — вернётся как есть (это не наша проблема)."""
	temp_cache.write_text("[1, 2, 3]", encoding="utf-8")
	# json.load вернёт список, но это не сломает скрипт сразу,
	# потому что дальше идёт проверка `if k in cache`
	result = mt.load_cache()
	assert result == [1, 2, 3]


# ─── save_cache ───────────────────────────────────────────────────

def test_save_cache_creates_file(temp_cache):
	"""save_cache создаёт файл."""
	assert not temp_cache.exists()
	mt.save_cache({"hash1": "перевод"})
	assert temp_cache.exists()


def test_save_cache_creates_directory(tmp_path, monkeypatch):
	"""Если директории нет — она создаётся."""
	nested = tmp_path / "deep" / "nested" / "translate_ru.json"
	monkeypatch.setattr(mt, "CACHE_FILE", str(nested))
	mt.save_cache({"a": "б"})
	assert nested.exists()
	assert nested.parent.is_dir()


def test_save_cache_writes_valid_json(temp_cache):
	"""Записанный JSON читается обратно."""
	data = {"hash1": "перевод1", "hash2": "перевод2"}
	mt.save_cache(data)
	with open(temp_cache, encoding="utf-8") as f:
		loaded = json.load(f)
	assert loaded == data


def test_save_cache_keeps_cyrillic_unescaped(temp_cache):
	"""ensure_ascii=False — русские буквы в файле как есть, не \\uXXXX."""
	mt.save_cache({"hash1": "привет"})
	raw = temp_cache.read_text(encoding="utf-8")
	assert "привет" in raw
	assert "\\u" not in raw


def test_save_cache_overwrites(temp_cache):
	"""Повторная запись перезаписывает файл."""
	mt.save_cache({"a": "1"})
	mt.save_cache({"b": "2"})
	with open(temp_cache, encoding="utf-8") as f:
		loaded = json.load(f)
	assert loaded == {"b": "2"}


def test_save_cache_error_warns_once(temp_cache, monkeypatch, capsys):
	"""При ошибке записи печатает [warn] в stderr только один раз."""
	def fake_open(*args, **kwargs):
		raise PermissionError("нельзя писать")

	monkeypatch.setattr("builtins.open", fake_open)

	mt.save_cache({"a": "б"})
	captured = capsys.readouterr()
	assert "не удалось сохранить кэш" in captured.err

	# Второй вызов — уже не должен ничего печатать (флаг _cache_warned)
	mt.save_cache({"c": "г"})
	captured = capsys.readouterr()
	assert "не удалось сохранить кэш" not in captured.err


# ─── round-trip ───────────────────────────────────────────────────

def test_save_then_load_roundtrip(temp_cache):
	"""save_cache → load_cache возвращает то же самое."""
	data = {"hash1": "перевод1", "hash2": "перевод2", "hash3": "Hello"}
	mt.save_cache(data)
	assert mt.load_cache() == data