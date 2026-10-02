"""Тесты для process — главной функции скрипта.

Мокаем lt_translate, чтобы не ходить в сеть.
Проверяем:
- базовый перевод (одна строка, много строк, пустой ввод);
- работу кэша (попадание, промах, fallback не кэшируется);
- батчинг (склейка коротких строк, разбиение длинных);
- help-строки (prefix не переводится, body переводится);
- сохранение отступов и хвостовых пробелов;
- fallback при несовпадении числа строк.
"""
import pytest

from utils import mymemory_translator as mt


@pytest.fixture
def mock_translate(mocker):
	"""Мок lt_translate, возвращающий успех по умолчанию.

	Каждый тест настраивает .side_effect или .return_value сам.
	"""
	return mocker.patch("utils.mymemory_translator.lt_translate")


# ─── Базовые случаи ───────────────────────────────────────────────

def test_process_empty_input(mock_translate):
	out = mt.process("", {})
	assert out == ""
	mock_translate.assert_not_called()


def test_process_whitespace_only(mock_translate):
	out = mt.process("   \n\n  ", {})
	assert out == "   \n\n  "
	mock_translate.assert_not_called()


def test_process_single_line(mock_translate):
	mock_translate.return_value = ("привет", True)
	out = mt.process("hello", {})
	assert out == "привет"
	mock_translate.assert_called_once()


def test_process_two_lines(mock_translate):
	mock_translate.return_value = ("привет\nмир", True)
	out = mt.process("hello\nworld", {})
	assert out == "привет\nмир"


# ─── Кэш ─────────────────────────────────────────────────────────

def test_process_uses_cache(mock_translate):
	"""Попадание в кэш — lt_translate не вызывается."""
	k = mt.key("hello")
	cache = {k: "привет"}
	out = mt.process("hello", cache)
	assert out == "привет"
	mock_translate.assert_not_called()


def test_process_fills_cache(mock_translate):
	"""Промах — перевод идёт в кэш."""
	mock_translate.return_value = ("привет", True)
	cache = {}
	mt.process("hello", cache)
	assert cache[mt.key("hello")] == "привет"


def test_process_fallback_not_cached(mock_translate):
	"""Fallback (ok=False) — в кэш НЕ попадает."""
	mock_translate.return_value = ("hello", False)
	cache = {}
	out = mt.process("hello", cache)
	assert out == "hello"
	assert mt.key("hello") not in cache


def test_process_mixed_cache_and_miss(mock_translate):
	"""Часть строк из кэша, часть — новые."""
	cache = {mt.key("hello"): "привет"}
	mock_translate.return_value = ("мир", True)
	out = mt.process("hello\nworld", cache)
	assert "привет" in out
	assert "мир" in out


def test_process_cyrillic_not_cached_not_translated(mock_translate):
	"""Кириллица пропускается — в кэш не идёт."""
	cache = {}
	out = mt.process("Привет, мир", cache)
	assert out == "Привет, мир"
	mock_translate.assert_not_called()
	assert cache == {}


# ─── Батчинг ─────────────────────────────────────────────────────

def test_process_batching_small(mock_translate):
	"""5 коротких строк — один вызов lt_translate."""
	mock_translate.return_value = ("a\nb\nc\nd\ne", True)
	out = mt.process("one\ntwo\nthree\nfour\nfive", {})
	assert mock_translate.call_count == 1
	assert out == "a\nb\nc\nd\ne"


def test_process_batching_split(mock_translate):
	"""Длинные строки — несколько вызовов."""
	# Каждая строка длиннее MAX_CHUNK, батчи не склеиваются
	long = "x" * (mt.MAX_CHUNK + 100)

	def fake_translate(text, source="en", target="ru"):
		# Возвращаем столько же строк, сколько пришло
		return ("\n".join("перевод" for _ in text.split("\n")), True)

	mock_translate.side_effect = fake_translate
	mt.process(f"{long}\n{long}", {})
	# Должно быть 2 вызова: по одному на каждую длинную строку
	assert mock_translate.call_count >= 2


def test_process_batch_line_count_mismatch(mock_translate, capsys):
	"""Батч вернул не то число строк → fallback построчно."""
	# Батч вернёт 1 строку вместо 3 → fallback
	mock_translate.side_effect = [
		("одна", True),  # батч
		("перевод1", True),  # строка 1
		("перевод2", True),  # строка 2
		("перевод3", True),  # строка 3
	]
	out = mt.process("a\nb\nc", {})
	captured = capsys.readouterr()
	assert "не совпало число строк" in captured.err
	assert "перевод1" in out
	assert "перевод2" in out
	assert "перевод3" in out


def test_process_batch_failed_fallback(mock_translate):
	"""Батч вернул ok=False → fallback построчно."""
	mock_translate.side_effect = [
		("a\nb", False),  # батч упал
		("перевод A", True),
		("перевод B", True),
	]
	out = mt.process("a\nb", {})
	assert "перевод A" in out
	assert "перевод B" in out


# ─── Help-строки ─────────────────────────────────────────────────

def test_process_help_line_prefix_not_translated(mock_translate):
	"""Строка '  run    Run a command' — prefix не переводится."""
	mock_translate.return_value = ("Выполнить команду", True)
	line = "  run       Run a command"
	out = mt.process(line, {})
	# prefix '  run       ' сохранён
	assert out.startswith("  run       ")
	assert "Выполнить команду" in out


def test_process_help_line_with_two_tokens(mock_translate):
	"""Строка с двумя токенами в команде: '  --flag <VAL>    Description'."""
	mock_translate.return_value = ("Описание", True)
	line = "  --flag <VAL>       Description"
	out = mt.process(line, {})
	assert out.startswith("  --flag <VAL>")
	assert "Описание" in out


def test_process_normal_indented_line(mock_translate):
	"""Обычная строка с отступом (не help) — переводится целиком."""
	mock_translate.return_value = ("  перевод", True)
	out = mt.process("  hello", {})
	assert "перевод" in out


# ─── Отступы и пробелы ───────────────────────────────────────────

def test_process_leading_spaces_preserved(mock_translate):
	mock_translate.return_value = ("привет", True)
	out = mt.process("    hello", {})
	assert out == "    привет"


def test_process_trailing_spaces_preserved(mock_translate):
	mock_translate.return_value = ("привет", True)
	out = mt.process("hello    ", {})
	assert out == "привет    "


def test_process_tab_indent_preserved(mock_translate):
	mock_translate.return_value = ("привет", True)
	out = mt.process("\thello", {})
	assert out == "\tпривет"


def test_process_mixed_indents(mock_translate):
	"""Строки с разными отступами — все сохраняются."""
	mock_translate.return_value = ("a\nb\nc", True)
	out = mt.process("    a\n\tb\nc", {})
	assert out == "    a\n\tb\nc"


# ─── Смешанный ввод ──────────────────────────────────────────────

def test_process_skip_and_translate_mixed(mock_translate):
	"""Чередование пропускаемых и переводимых строк."""
	mock_translate.return_value = ("перевод", True)
	text = "Привет\nhello\n$ ls"
	out = mt.process(text, {})
	lines = out.split("\n")
	assert lines[0] == "Привет"       # кириллица — как есть
	assert "перевод" in lines[1]      # английский — переведён
	assert lines[2] == "$ ls"          # команда — как есть


def test_process_only_skipped_lines(mock_translate):
	"""Если всё пропускается — lt_translate не вызывается."""
	text = "Привет\n$ ls\n  File \"x.py\", line 1"
	out = mt.process(text, {})
	assert out == text
	mock_translate.assert_not_called()


# ─── Пустые строки внутри ────────────────────────────────────────

def test_process_empty_line_between(mock_translate):
	"""Пустая строка внутри текста сохраняется."""
	mock_translate.return_value = ("a\n\nb", True)
	out = mt.process("a\n\nb", {})
	assert "\n\n" in out


# ─── Кэш: частичный fallback ─────────────────────────────────────

def test_process_partial_fallback_caching(mock_translate):
	"""Если fallback сработал только для части — успешные всё равно в кэш."""
	# Первый батч упал, построчно: 1-я — успех, 2-я — провал
	mock_translate.side_effect = [
		("a\nb", False),   # батч
		("перевод A", True),
		("b", False),      # вторая строка не перевелась
	]
	cache = {}
	mt.process("a\nb", cache)
	assert mt.key("a") in cache
	assert mt.key("b") not in cache