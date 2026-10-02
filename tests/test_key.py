"""Тесты для функции key.

Проверяем, что MD5-хеш:
- детерминирован (одинаковый вход → одинаковый выход);
- чувствителен к регистру и содержанию;
- корректен для кириллицы;
- выдаёт 32 символа в hex-формате.
"""
import re

import pytest

from utils.mymemory_translator import key


def test_key_is_deterministic():
	assert key("hello") == key("hello")
	assert key("world") == key("world")


def test_key_differs_for_different_input():
	assert key("hello") != key("world")
	assert key("abc") != key("abcd")


def test_key_case_sensitive():
	assert key("hello") != key("Hello")
	assert key("HELLO") != key("Hello")


def test_key_length_is_32():
	assert len(key("")) == 32
	assert len(key("hello")) == 32
	assert len(key("a" * 1000)) == 32


@pytest.mark.parametrize("text", [
	"hello",
	"Hello, World!",
	"  с пробелами  ",
	"привет",
	"Ёжик",
	"test\nwith\nnewlines",
	"спецсимволы !@#$%^&*()",
	"",
])
def test_key_format_is_hex(text):
	k = key(text)
	assert re.fullmatch(r"[0-9a-f]{32}", k), f"не hex: {k}"


def test_key_known_value():
	"""Проверка на известное значение: md5('hello') = 5d41402abc4b2a76b9719d911017c592."""
	assert key("hello") == "5d41402abc4b2a76b9719d911017c592"


def test_key_cyrillic():
	"""Кириллица должна хешироваться как UTF-8."""
	assert key("привет") == key("привет")
	assert key("привет") != key("Привет")