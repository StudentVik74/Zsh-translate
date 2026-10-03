"""Тесты для функции should_skip."""
import pytest

from utils.translate import should_skip


# ─── Пустые строки ────────────────────────────────────────────────

@pytest.mark.parametrize("line", ["", "   ", "\t", "\n", "   \t  "])
def test_empty_and_whitespace_lines_are_skipped(line):
	assert should_skip(line) is True


# ─── Кириллица ────────────────────────────────────────────────────

@pytest.mark.parametrize("line", [
	"Привет, мир",
	"ошибка: файл не найден",
	"  Команда выполнена",
	"Тест passed",
	"Ёжик",
])
def test_cyrillic_lines_are_skipped(line):
	assert should_skip(line) is True


def test_english_line_is_not_skipped():
	assert should_skip("Hello, world") is False


# ─── Командные строки ─────────────────────────────────────────────

@pytest.mark.parametrize("line", [
	"$ ls -la",
	"# comment",
	"> echo test",
	"  $ pwd",
])
def test_shell_prompts_are_skipped(line):
	assert should_skip(line) is True


# ─── Traceback ────────────────────────────────────────────────────

@pytest.mark.parametrize("line", [
	'  File "app.py", line 5, in <module>',
	"  at com.example.Main(Main.java:42)",
	"app.py:15:3: error: expected expression",
	"/home/user/project/module.py:42:1: warning: unused import",
])
def test_traceback_lines_are_skipped(line):
	assert should_skip(line) is True


# ─── Смешанные случаи ─────────────────────────────────────────────

@pytest.mark.parametrize("line, expected", [
	("", True),
	("Hello world", False),
	("Hello, мир", True),
	("ERROR: file not found", False),
	("ОШИБКА: файл не найден", True),
	("$ echo hello", True),
	("path/to/file.py:10:5: note", True),
])
def test_mixed_cases(line, expected):
	assert should_skip(line) is expected