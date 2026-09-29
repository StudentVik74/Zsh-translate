#!/usr/bin/env python3
"""
Перевод stdin на русский через MyMemory API.

- Батчинг(пакет): соседние строки склеиваются в один запрос.
- Кэш: только успешные переводы.
- Проверка API: одно предупреждение при первой ошибке, затем тишина.
"""
import sys
import os
import re
import json
import hashlib
import requests

CACHE_FILE     = os.path.expanduser("~/.cache/translate_ru/translate_ru.json")
LT_URL         = "https://api.mymemory.translated.net/get"
MYMEMORY_EMAIL = ""     # ← впиши свой email для лимита 50000 символов/день
MAX_CHUNK      = 400    # MyMemory плохо переносит большие батчи

SKIP_PATTERNS = [
	re.compile(r'^\s*[\$#>]\s'),
	re.compile(r'^\s*at .+\(.*:\d+\)'),
	re.compile(r'^\s*File ".+"'),
	re.compile(r'^\s*[\w\-\./]+:\d+:\d+:'),
]

# Кириллица где угодно в строке — признак, что текст уже на русском
CYRILLIC_RE = re.compile(r'[а-яА-ЯёЁ]')

# Флаг: предупреждение о недоступности API
_api_warned = False


def should_skip(line: str) -> bool:
	"""Определяет, следует ли пропустить строку при переводе.

	Строка будет пропущена, если:
	  - она пустая или содержит только пробелы;
	  - совпадает с одним из паттернов SKIP_PATTERNS (командные строки,
	    трейсы, пути к файлам и т.п.); —
	  - содержит кириллицу (признак того, что текст уже на русском).

	Args:
		line: Входная строка для проверки.

	Returns:
		True — строку нужно пропустить, False — перевести.
	"""
	if not line.strip():
		return True
	if any(p.match(line) for p in SKIP_PATTERNS):
		return True
	if CYRILLIC_RE.search(line):
		return True
	return False


def key(s: str) -> str:
	"""Вычисляет MD5-хеш строки.

	Используется для создания уникальных ключей кэша переводов.

	Args:
		s: Входная строка для хеширования.

	Returns:
		MD5-хеш строки в шестнадцатеричном формате (32 символа).
	"""
	return hashlib.md5(s.encode("utf-8")).hexdigest()


def load_cache() -> dict:
	"""Загружает кэш переводов из JSON-файла.

	Попытки прочитать файл:
	  - если файл не существует — вернёт пустой словарь;
	  - если файл повреждён или не является валидным JSON — вернёт пустой словарь;
	  - при любой другой ошибке — вернёт пустой словарь.

	Returns:
		Словарь кэша в формате {hash: translation}, или пустой словарь при ошибке.
	"""
	try:
		with open(CACHE_FILE, encoding="utf-8") as f:
			return json.load(f)
	except Exception:
		return {}


def save_cache(cache: dict) -> None:
	"""Сохраняет кэш переводов в JSON-файл.

	Перед записью создаёт директорию кэша, если она не существует.
	Все ошибки (нехватка прав, полный диск и т.п.) игнорируются.

	Args:
		cache: Словарь для сохранения в формате {hash: translation}.
	"""
	try:
		os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
		with open(CACHE_FILE, "w", encoding="utf-8") as f:
			json.dump(cache, f, ensure_ascii=False)
	except Exception:
		pass


def check_quota() ->  bool | None:
	"""Проверить квоту MyMemory.

	Возвращает:
		True — квота исчерпана;
		False — квота не исчерпана;
		None — не удалось проверить (сеть, таймаут).
	"""
	try:
		params = {"q": "test", "langpair": "en|ru"}
		if MYMEMORY_EMAIL:
			params["de"] = MYMEMORY_EMAIL
		r = requests.get(LT_URL, params=params, timeout=10)
		data = r.json()
		if data.get("quotaFinished"):
			return True
		status = data.get("responseStatus")
		if status and int(status) == 429:
			return True
		return False
	except Exception:
		return None


def notify_first_failure(e) -> None:
	"""Выводит предупреждение об ошибке API один раз за сеанс работы.

	При первом вызове:
	  1. Выводит сообщение об ошибке в stderr.
	  2. Проверяет квоту MyMemory API.
	  3. Выводит дополнительную подсказку:
	     - если квота исчерпана — сообщает о сбросе квоты;
	     - если квота не исчерпана — указывает на возможную проблему сети.

	Повторные вызовы игнорируются (флаг _api_warned).

	Args:
		e: Исключение, возникшее при запросе к MyMemory API.
	"""
	global _api_warned
	if _api_warned:
		return
	_api_warned = True

	print(f"[warn] MyMemory недоступен: {e!r}", file=sys.stderr)

	quota = check_quota()
	if quota is True:
		print("[warn] квота MyMemory исчерпана — "
		      "перевод не работает до завтра (UTC)", file=sys.stderr)
	elif quota is False:
		print("[warn] квота не исчерпана — "
		      "вероятно, проблема с сетью или сервером", file=sys.stderr)


def lt_translate(text: str, source: str = "en", target: str = "ru") -> tuple[str, bool]:
	"""Переводит текст через MyMemory API.

	Отправляет текст на перевод с указанного источника на целевой язык.
	При успешном ответе с status 200 возвращает переведённый текст.
	При любой ошибке (сеть, таймаут, неверный статус, повреждённый JSON)
	выводит предупреждение (один раз) и возвращает исходный текст.

	Args:
		text:      Текст для перевода.
		source:    Код языка источника (по умолчанию "en").
		target:    Код языка перевода (по умолчанию "ru").

	Returns:
		Кортеж (translated_text: str, success: bool):
		  - (перевод, True)  — при успешном переводе;
		  - (исходный текст, False) — при ошибке.
	"""
	try:
		params = {
			"q": text,
			"langpair": f"{source}|{target}",
		}
		if MYMEMORY_EMAIL:
			params["de"] = MYMEMORY_EMAIL

		r = requests.get(LT_URL, params=params, timeout=30)
		r.raise_for_status()
		data = r.json()

		status = data.get("responseStatus")
		if status and int(status) != 200:
			raise RuntimeError(
				f"MyMemory вернул статус {status}: "
				f"{data.get('responseDetails') or 'без деталей'}"
			)

		return data["responseData"]["translatedText"], True
	except Exception as e:
		notify_first_failure(e)
		return text, False


def process(text: str, cache: dict) -> str:
	"""Обрабатывает текст: переводит строки с использованием кэша и API.

	Алгоритм:
	  1. Разбивает текст на строки.
	  2. Отфильтровывает строки, которые не нужно переводить (пустые,
	     уже на русском, командные строки и т.п.).
	  3. Группирует строки, требующие перевода, в пакеты (батчи) по ≤ 400 символов.
	  4. Отправляет пакеты в MyMemory API; при неудаче переводит построчно.
	  5. Кэширует только успешные переводы.
	  6. Собирает результат, сохраняя отступы и переносы строк.

	Args:
		text:  Входной текст для обработки.
		cache: Текущий кэш переводов {hash: translation}.

	Returns:
		Переведённый текст с сохранением структуры (отступы, переносы).
	"""

	for line in lines:
		if should_skip(line):
			plan.append({"type": "raw", "value": line})
			continue
		m = re.match(r'^(\s*)(.*?)(\s*)$', line, re.DOTALL)
		indent, body, trail = m.group(1), m.group(2), m.group(3)
		k = key(body)
		if k in cache:
			plan.append({"type": "cached", "value": indent + cache[k] + trail})
		else:
			plan.append({"type": "pending", "body": body,
			             "indent": indent, "trail": trail,
			             "k": k, "value": None})

	i = 0
	while i < len(plan):
		if plan[i]["type"] != "pending":
			i += 1
			continue
		j, size = i, 0
		while (j < len(plan)
		       and plan[j]["type"] == "pending"
		       and size + len(plan[j]["body"]) < MAX_CHUNK):
			size += len(plan[j]["body"]) + 1
			j += 1

		batch  = plan[i:j]
		bodies = [b["body"] for b in batch]

		# Список кортежей (перевод, успех) — по одному на каждую строку батча
		results = []

		# 1. Пытаемся перевести весь батч(пакет) одним запросом
		translated, ok = lt_translate("\n".join(bodies))
		if ok:
			parts = translated.split("\n")
			if len(parts) == len(bodies):
				results = [(p, True) for p in parts]
			else:
				print(f"[внимание!] пакет не переведён: не совпало число строк "
				      f"({len(parts)} != {len(bodies)})", file=sys.stderr)

		# 2. Если батч(пакет) не прошёл — переводим построчно
		if not results:
			for b in bodies:
				results.append(lt_translate(b))

		# 3. Применяем результаты, кэшируем только успешные
		for b, (tr, line_ok) in zip(batch, results):
			b["value"] = b["indent"] + tr + b["trail"]
			if line_ok:
				cache[b["k"]] = tr

		i = j

	return "\n".join(p["value"] for p in plan)


def main() -> None:
	"""Точка входа: читает stdin, переводит, пишет в stdout.

	Читает весь ввод из стандартного потока, загружает кэш,
	выполняет перевод через process(), сохраняет обновлённый кэш
	и выводит результат в stdout.
	Если входной текст заканчивается переносом строки, но перевод
	его «теряет», дописывает перенос вручную.
	"""
	text = sys.stdin.read()
	if not text.strip():
		return
	cache = load_cache()
	out = process(text, cache)
	save_cache(cache)
	sys.stdout.write(out)
	if text.endswith("\n") and not out.endswith("\n"):
		sys.stdout.write("\n")


if __name__ == "__main__":
	main()