"""Тесты для main — точки входа.

main() читает stdin, переводит, пишет stdout, сохраняет кэш.
Тестируем через monkeypatch (stdin) и capsys (stdout/stderr).

Проверяем:
- пустой ввод → пустой вывод, кэш не пишется;
- BOM (\ufeff) отрезается;
- перевод пишется в stdout;
- сохранение \n в конце;
- кэш сохраняется после перевода;
- кириллица не идёт в переводчик.
"""
import io
import json

import pytest

from utils import translate as mt


@pytest.fixture
def mock_translate(mocker):
	"""Мок lt_translate."""
	return mocker.patch("utils.mymemory_translator.lt_translate")


@pytest.fixture
def set_stdin(monkeypatch):
	"""Подменить sys.stdin на строковый поток."""
	def _set(text: str):
		monkeypatch.setattr("sys.stdin", io.StringIO(text))
	return _set


# ─── Пустой ввод ─────────────────────────────────────────────────

def test_main_empty_input(mock_translate, set_stdin, capsys, temp_cache):
	set_stdin("")
	mt.main()
	captured = capsys.readouterr()
	assert captured.out == ""
	mock_translate.assert_not_called()


def test_main_whitespace_only(mock_translate, set_stdin, capsys, temp_cache):
	"""Только пробелы/табы на входе → пустой вывод, переводчик не вызывается."""
	set_stdin("   \n\t\n  ")
	mt.main()
	captured = capsys.readouterr()
	assert captured.out == ""
	mock_translate.assert_not_called()


# ─── BOM ─────────────────────────────────────────────────────────

def test_main_strips_bom(mock_translate, set_stdin, capsys, temp_cache):
	"""BOM (\ufeff) в начале входа отрезается."""
	mock_translate.return_value = ("привет", True)
	set_stdin("\ufeffhello")
	mt.main()
	captured = capsys.readouterr()
	# BOM не должен попасть в перевод как часть текста
	assert "\ufeff" not in captured.out
	# lt_translate получил именно "hello", без BOM
	call_args = mock_translate.call_args
	assert call_args.args[0] == "hello"


# ─── Обычный перевод ─────────────────────────────────────────────

def test_main_basic_translate(mock_translate, set_stdin, capsys, temp_cache):
	mock_translate.return_value = ("привет", True)
	set_stdin("hello")
	mt.main()
	captured = capsys.readouterr()
	assert "привет" in captured.out


def test_main_multiline(mock_translate, set_stdin, capsys, temp_cache):
	mock_translate.return_value = ("привет\nмир", True)
	set_stdin("hello\nworld")
	mt.main()
	captured = capsys.readouterr()
	assert "привет" in captured.out
	assert "мир" in captured.out


def test_main_trailing_newline_preserved(mock_translate, set_stdin, capsys, temp_cache):
	"""Если вход заканчивается на \n, выход тоже."""
	mock_translate.return_value = ("привет", True)
	set_stdin("hello\n")
	mt.main()
	captured = capsys.readouterr()
	assert captured.out.endswith("\n")


# ─── Кэш ─────────────────────────────────────────────────────────

def test_main_saves_cache(mock_translate, set_stdin, capsys, temp_cache):
	"""После main() кэш-файл создан и содержит перевод."""
	mock_translate.return_value = ("привет", True)
	set_stdin("hello")
	mt.main()

	assert temp_cache.exists()
	with open(temp_cache, encoding="utf-8") as f:
		cache = json.load(f)
	assert cache[mt.key("hello")] == "привет"


def test_main_uses_cache(mock_translate, set_stdin, capsys, temp_cache):
	"""Если перевод уже в кэше — lt_translate не вызывается."""
	# Заранее кладём в кэш
	cache = {mt.key("hello"): "привет"}
	temp_cache.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

	set_stdin("hello")
	mt.main()
	captured = capsys.readouterr()
	assert "привет" in captured.out
	mock_translate.assert_not_called()


def test_main_does_not_cache_fallback(mock_translate, set_stdin, capsys, temp_cache):
	"""Fallback (ok=False) не должен попасть в кэш."""
	mock_translate.return_value = ("hello", False)
	set_stdin("hello")
	mt.main()

	assert temp_cache.exists()
	with open(temp_cache, encoding="utf-8") as f:
		cache = json.load(f)
	assert mt.key("hello") not in cache


# ─── Кириллица ───────────────────────────────────────────────────

def test_main_cyrillic_passthrough(mock_translate, set_stdin, capsys, temp_cache):
	"""Русский текст не идёт в переводчик, выводится как есть."""
	set_stdin("Привет, мир")
	mt.main()
	captured = capsys.readouterr()
	assert "Привет, мир" in captured.out
	mock_translate.assert_not_called()


# ─── Ошибка API ──────────────────────────────────────────────────

def test_main_api_error_returns_original(mock_translate, set_stdin, capsys, temp_cache):
	"""При ошибке API оригинал выводится, но не падает."""
	mock_translate.return_value = ("hello", False)
	set_stdin("hello")
	mt.main()
	captured = capsys.readouterr()
	assert "hello" in captured.out


# ─── Кодировка вывода ────────────────────────────────────────────

def test_main_output_is_str(mock_translate, set_stdin, capsys, temp_cache):
	"""stdout получает текст, а не байты."""
	mock_translate.return_value = ("привет", True)
	set_stdin("hello")
	mt.main()
	captured = capsys.readouterr()
	assert isinstance(captured.out, str)