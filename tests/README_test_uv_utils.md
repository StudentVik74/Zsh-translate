# Тесты

Тестирование `translate.py` через **pytest**. Управление зависимостями — через **uv**.

## Требования

- **uv** ≥ 0.11
- **Python** ≥ 3.10

Проверить:

    uv --version
    python --version

Если `uv` ещё не установлен:

    # Linux / macOS
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Windows (PowerShell)
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

---

## Первичная настройка

Выполняется **один раз** из корня проекта (там, где лежит `pyproject.toml`).

### 1. Добавить dev-зависимости

    uv add --dev pytest pytest-mock pytest-cov

Что произойдёт:

- В `pyproject.toml` появится секция `[dependency-groups]` с тремя пакетами.
- Создастся `uv.lock` — файл блокировки версий.
- Создастся `.venv/` — виртуальное окружение.

Пример содержимого `pyproject.toml`:

    [dependency-groups]
    dev = [
        "pytest>=8.1.1,<9",
        "pytest-mock>=3.14.0",
        "pytest-cov>=6.0.0",
    ]

### 2. Проверить, что всё установилось

    uv run pytest --version

Должно вывести версию pytest, например `pytest 8.3.5`.

---

## Запуск тестов

Все команды выполняются **из корня проекта**.

### Все тесты

    uv run pytest

`uv run` сам:
1. Проверит, что `.venv` синхронизировано с `pyproject.toml`.
2. Доустановит недостающие пакеты (быстро, из кэша).
3. Запустит pytest в этом окружении.

**Активировать `.venv` вручную не нужно** — `uv run` делает это автоматически.

### Подробный вывод

    uv run pytest -v

Показывает имя каждого теста и результат (`PASSED` / `FAILED`).

### Конкретный файл

    uv run pytest tests/test_should_skip.py -v

### Конкретный тест

    uv run pytest tests/test_should_skip.py::test_empty_line -v

### С покрытием

    uv run pytest --cov=translate --cov-report=term-missing

Показывает процент покрытия и **непокрытые строки**.

### Только быстрые тесты (без интеграционных)

    uv run pytest -m "not integration"

Интеграционные тесты (реальный MyMemory API) пропускаются. Это **режим по умолчанию для повседневной работы** — быстро и не тратит квоту.

### Только интеграционные

    uv run pytest -m integration -v

Требуют интернета и **тратят квоту MyMemory**. Запускать редко — перед релизом.

---

## Полезные флаги

| Команда | Что делает |
|---|---|
| `uv run pytest -v` | Подробный вывод |
| `uv run pytest -x` | Остановиться на первой ошибке |
| `uv run pytest -s` | Показать stdout/stderr (для `capsys`) |
| `uv run pytest --lf` | Только тесты, упавшие в прошлый раз |
| `uv run pytest --ff` | Сначала упавшие, потом остальные |
| `uv run pytest --pdb` | Открыть отладчик в точке падения |
| `uv run pytest --durations=10` | Топ-10 самых медленных тестов |
| `uv run pytest -q` | Тихий вывод (только точки) |
| `uv run pytest --collect-only` | Показать список тестов без запуска |

Комбинировать можно:

    uv run pytest tests/test_process.py -v -s --pdb

---

## Полный рабочий процесс

    # 1. Первичная настройка (один раз)
    uv add --dev pytest pytest-mock pytest-cov

    # 2. Запуск всех быстрых тестов
    uv run pytest -m "not integration" -v

    # 3. С покрытием
    uv run pytest -m "not integration" --cov=translate --cov-report=term-missing

    # 4. Если добавил новую dev-зависимость вручную в pyproject.toml
    uv sync --dev

    # 5. Только упавшие в прошлый раз
    uv run pytest --lf

    # 6. Интеграционные (редко)
    uv run pytest -m integration -v

---

## Управление зависимостями

### Добавить пакет

    uv add --dev имя-пакета

Например:

    uv add --dev pytest-timeout

### Удалить пакет

    uv remove --dev pytest-timeout

### Обновить все пакеты

    uv lock --upgrade
    uv sync --dev

### Синхронизировать окружение с pyproject.toml

    uv sync --dev

Установит **все** зависимости (включая dev), даже если `.venv` отсутствует.

### Синхронизировать только продакшн-зависимости

    uv sync

Установит только то, что нужно для запуска `translate.py` (например, `requests`), без dev-пакетов.

---

## Структура тестов

    tests/
    ├── README.md                 — этот файл
    ├── conftest.py               — общие фикстуры
    ├── test_should_skip.py       — фильтр строк
    ├── test_key.py               — MD5-хеш
    ├── test_cache.py             — чтение/запись кэша
    ├── test_quota.py             — проверка квоты MyMemory
    ├── test_lt_translate.py      — основной перевод
    ├── test_process.py           — батчинг, кэш, help-строки
    └── test_main.py              — точка входа (end-to-end)

---

## Что тестируется

### 1. `should_skip(line)` — фильтр строк

Определяет, нужно ли пропустить строку при переводе.

| Вход | Ожидание | Почему |
|---|---|---|
| `""` | `True` | нечего переводить |
| `"   "` | `True` | только пробелы |
| `"Привет, мир"` | `True` | кириллица |
| `"Hello, world"` | `False` | английский |
| `"$ ls -la"` | `True` | командная строка |
| `"  File \"app.py\", line 5"` | `True` | traceback |
| `"app.py:15:3: error"` | `True` | gcc/clang |

### 2. `key(s)` — MD5-хеш строки

Ключ кэша.

- Детерминированность: `key("hello") == key("hello")`
- Регистр важен: `key("hello") != key("Hello")`
- Длина — 32 символа
- Формат — `^[0-9a-f]{32}$`
- Кириллица: `key("привет")` работает

### 3. `load_cache()` / `save_cache(cache)`

Чтение/запись кэша переводов.

**`load_cache`:** нет файла → `{}`, битый JSON → `{}`, валидный → словарь.

**`save_cache`:** создаёт директорию, пишет JSON, `ensure_ascii=False`, при ошибке пишет `[warn]` один раз.

Изолируется через фикстуру `tmp_path` (реальный `~/.cache/` не трогается).

### 4. `check_quota()` — проверка квоты MyMemory

- `quotaFinished: true` → `True`
- `responseStatus: 429` → `True`
- Успешный ответ → `False`
- Сеть упала → `None`

Мок `requests.get` через `pytest-mock`.

### 5. `notify_first_failure(e)` — одноразовое предупреждение

- Первый вызов → печатает `[warn]` в stderr
- Второй и далее → **молчит**
- Проверка квоты: `True` → «квота исчерпана», `False` → «проблема с сетью»

Перехват stderr через `capsys`, сброс флага через фикстуру `reset_flags`.

### 6. `lt_translate(text)` — основной перевод

- Успех → `("перевод", True)`
- HTTP 500 / 429 → `("оригинал", False)`
- `responseStatus != 200` → fallback
- Битый JSON → fallback
- `ConnectionError`, `Timeout` → fallback
- Параметр `de` (email) присутствует, если `MYMEMORY_EMAIL` задан

Проверяется корректность параметров запроса (`q`, `langpair`, `timeout`).

### 7. `process(text, cache)` — главная логика

Самая «мясная» функция.

**Базовые:** одна строка, много строк, пустой ввод.

**Кэш:** попадание в кэш → `lt_translate` **не вызывается**; промах → вызывается и пополняет.

**Батчинг:** короткие строки → один вызов; длинные → несколько; разное число строк в ответе → fallback построчно.

**Help-строки:** `"  run    Run a command"` → prefix не переводится, body переводится.

**Отступы:** ведущие пробелы, хвостовые, `\t` — сохраняются.

### 8. `main()` — точка входа

Читает stdin, пишет stdout, сохраняет кэш.

- Пустой stdin → пустой stdout
- BOM (`\ufeff`) отрезается
- Обычный текст → перевод + `\n` при необходимости
- Русский текст → как есть

Через `monkeypatch` (stdin) и `capsys` (stdout).

---

## Фикстуры (`conftest.py`)

### `temp_cache`

Подменяет `CACHE_FILE` на `tmp_path`. Изолирует тесты от `~/.cache/`.

### `reset_flags` (autouse)

Сбрасывает `_api_warned` и `_cache_warned` перед каждым тестом. Гарантирует, что состояние не протекает между тестами.

### `mock_requests`

Возвращает мок `translate.requests.get`. Каждый тест настраивает ответ под себя.

---

## Категории тестов

### Быстрые (по умолчанию)

Без сети, без реальных файлов. Запускаются за доли секунды:

    uv run pytest -m "not integration"

### Медленные (интеграционные)

Помечены `@pytest.mark.integration`. Тратят квоту MyMemory:

    uv run pytest -m integration -v

**Не включаются в CI по умолчанию** — иначе каждый push будет есть квоту.

---

## Маркеры pytest

В `pyproject.toml`:

    [tool.pytest.ini_options]
    markers = [
        "integration: тесты, требующие реальный MyMemory API (медленно, тратит квоту)",
    ]

Без регистрации маркеров pytest выдаёт warning.

---

## Покрытие (coverage)

Цель — **85–90%**.

    uv run pytest -m "not integration" --cov=translate --cov-report=term-missing

Отчёт покажет непокрытые строки.

**Ожидаемо непокрытыми могут остаться:**

- ветки `except Exception` для экзотических ошибок (`MemoryError`);
- код в `if __name__ == "__main__"`;
- редкие ветки fallback.

Это нормально. **100%** обычно недостижимо без искусственных тестов.

### HTML-отчёт покрытия

    uv run pytest --cov=translate --cov-report=html

Откроется `htmlcov/index.html` — наглядная визуализация.

---

## Что НЕ тестируется

1. Реальный сетевой доступ (кроме `@pytest.mark.integration`).
2. Поведение MyMemory при разных языках.
3. Логика zsh/PowerShell обёртки `ru`.
4. Кодировка на разных ОС (частично покрыто в `test_main.py`).

---

## Что делать, если тест падает

1. **`-v`** — увидеть, какой ассерт не прошёл.
2. **`-x`** — остановиться на первой ошибке.
3. **`-s`** — показать stdout/stderr (для `capsys`).
4. **`--pdb`** — открыть отладчик в точке падения.

Пример:

    uv run pytest tests/test_process.py::test_process_uses_cache -v -s --pdb

---

## Порядок написания

1. `test_should_skip.py` — без моков.
2. `test_key.py` — тривиально.
3. `test_cache.py` — фикстура `tmp_path`.
4. `test_quota.py` — первый опыт с моками.
5. `test_lt_translate.py` — основная логика.
6. `test_process.py` — самый важный файл.
7. `test_main.py` — end-to-end.
8. Интеграционные — в самом конце.

---

## Дальнейшие шаги

1. **GitHub Actions** — автозапуск `uv run pytest` при push и pull request.
2. **Codecov / Coveralls** — измерение покрытия в CI.
3. **Badge в README** — «tests passing» и «coverage X%».
4. **Pre-commit hook** — автозапуск быстрых тестов перед коммитом.