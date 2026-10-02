# Тесты

Тестирование `translate.py` через **pytest**.

## Структура

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

## Установка

    pip3 install pytest pytest-mock pytest-cov

Или на Ubuntu с PEP 668:

    pip3 install --user --break-system-packages pytest pytest-mock pytest-cov

## Запуск

    # все тесты
    pytest tests/ -v

    # только конкретный файл
    pytest tests/test_should_skip.py -v

    # только конкретный тест
    pytest tests/test_should_skip.py::test_empty_line -v

    # с покрытием
    pytest tests/ --cov=translate --cov-report=term-missing

    # без интеграционных (быстро)
    pytest tests/ -m "not integration"

    # только интеграционные (реальный API, медленно)
    pytest tests/ -m integration

---

## Что тестируется

### 1. `should_skip(line)` — фильтр строк

**Назначение:** определяет, нужно ли пропустить строку при переводе.

**Случаи, которые надо проверить:**

| Вход | Ожидание | Почему |
|---|---|---|
| `""` (пустая строка) | `True` | нечего переводить |
| `"   "` (только пробелы) | `True` | нечего переводить |
| `"Привет, мир"` | `True` | уже на русском |
| `"Hello, world"` | `False` | английский → переводить |
| `"$ ls -la"` | `True` | командная строка |
| `"# comment"` | `True` | комментарий |
| `"  File \"app.py\", line 5"` | `True` | python traceback |
| `"  at com.example.Main(Main.java:42)"` | `True` | java stacktrace |
| `"app.py:15:3: error: ..."` | `True` | gcc/clang warning |
| `"Docker: невозможно..."` | `True` | кириллица |
| `"Docker: cannot connect"` | `False` | переводить |

**Как тестируется:** чистые функции без моков. Параметризация через `@pytest.mark.parametrize`.

---

### 2. `key(s)` — MD5-хеш строки

**Назначение:** ключ кэша.

**Случаи:**

| Проверка | Ожидание |
|---|---|
| `key("hello") == key("hello")` | одинаковый хеш для одинакового входа |
| `key("hello") != key("Hello")` | разный регистр → разный хеш |
| `key("hello") != key("world")` | разный текст → разный хеш |
| Длина хеша | 32 символа |
| Хеш только из `0-9a-f` | regex `^[0-9a-f]{32}$` |
| `key("привет")` работает | кириллица хешируется корректно |

**Как тестируется:** чистые вызовы, проверка свойств.

---

### 3. `load_cache()` и `save_cache(cache)` — чтение/запись кэша

**Назначение:** хранить успешные переводы между запусками.

**`load_cache` — случаи:**

| Ситуация | Ожидание |
|---|---|
| Файла нет | `{}` |
| Файл пустой | `{}` |
| Файл с валидным JSON | словарь с данными |
| Файл с битым JSON | `{}` |
| Файл без прав на чтение | `{}` |

**`save_cache` — случаи:**

| Ситуация | Ожидание |
|---|---|
| Директория не существует | создаётся, файл пишется |
| Директория существует | файл перезаписывается |
| Русские буквы в значениях | сохраняются как есть (`ensure_ascii=False`) |
| Нет прав на запись | не падает, выводит `[warn]` в stderr |

**Как тестируется:** фикстура `tmp_path` (встроенная в pytest) подменяет `CACHE_FILE` на временный путь. Реальный `~/.cache/` не трогается.

**Пример:**

```python
def test_load_cache_no_file(tmp_path, monkeypatch):
    fake = tmp_path / "cache.json"
    monkeypatch.setattr(translate, "CACHE_FILE", str(fake))
    assert translate.load_cache() == {}
```

---

### 4. `check_quota()` — проверка квоты MyMemory

**Назначение:** узнать, исчерпана ли дневная квота.

**Случаи (с моком `requests.get`):**

| Ответ API | Ожидание |
|---|---|
| `{"quotaFinished": true, ...}` | `True` |
| `{"quotaFinished": false, "responseStatus": 200}` | `False` |
| `{"responseStatus": 429}` | `True` |
| Сеть упала (`ConnectionError`) | `None` |
| Таймаут (`Timeout`) | `None` |
| Битый JSON | `None` |
| С email и без | параметр `de` в запросе присутствует/отсутствует |

**Как тестируется:** мок `requests.get` через `pytest-mock` (`mocker.patch`). Никаких реальных запросов.

---

### 5. `notify_first_failure(e)` — одноразовое предупреждение

**Назначение:** не спамить одинаковыми ошибками.

**Случаи:**

| Проверка | Ожидание |
|---|---|
| Первый вызов | печатает `[warn] MyMemory недоступен` в stderr |
| Второй вызов | **не** печатает |
| Третий вызов | **не** печатает |
| Квота исчерпана (мок) | печатает строку про квоту |
| Квота не исчерпана (мок) | печатает строку про сеть |
| Квота неизвестна (мок `None`) | только базовое предупреждение |

**Как тестируется:** `capsys` (pytest) для перехвата stderr, сброс флага `_api_warned = False` между тестами через фикстуру.

---

### 6. `lt_translate(text)` — основной перевод

**Назначение:** отправить текст в MyMemory, получить перевод.

**Случаи (с моком `requests.get`):**

| Ответ API | Ожидание |
|---|---|
| `{"responseData": {"translatedText": "привет"}, "responseStatus": 200}` | `("привет", True)` |
| HTTP 500 | `(исходный текст, False)` |
| HTTP 429 | `(исходный текст, False)` |
| `responseStatus: 429` в JSON | `(исходный текст, False)` |
| `responseStatus: 403` в JSON | `(исходный текст, False)` |
| Битый JSON | `(исходный текст, False)` |
| `KeyError` (нет `responseData`) | `(исходный текст, False)` |
| `ConnectionError` | `(исходный текст, False)` |
| `Timeout` | `(исходный текст, False)` |
| С email — параметр `de` в запросе | присутствует |
| Без email — параметр `de` | отсутствует |

**Проверка корректности URL:**

Мок `requests.get` может записать переданные аргументы и проверить, что:
- `params["q"] == text`
- `params["langpair"] == "en|ru"`
- `timeout == 30`

**Интеграционный тест** (помечен `@pytest.mark.integration`):

```python
@pytest.mark.integration
def test_real_mymemory():
    text, ok = translate.lt_translate("Hello")
    assert ok is True
    assert len(text) > 0
    assert text != "Hello"
```

Запускается отдельно: `pytest -m integration`. **Тратит квоту MyMemory**, поэтому не в дефолтном наборе.

---

### 7. `process(text, cache)` — главная логика

**Назначение:** батчинг, кэш, help-строки, fallback.

Это самая «мясная» функция. Тестируется с моком `lt_translate`.

**Случаи:**

#### 7.1. Базовые

| Вход | Мок `lt_translate` | Ожидание |
|---|---|---|
| `"hello"` | `("привет", True)` | `"привет"` |
| `""` | не вызывается | `""` |
| `"hello\nworld"` | батчем → `("привет\nмир", True)` | `"привет\nмир"` |

#### 7.2. Кэш

| Вход | cache | Ожидание |
|---|---|---|
| `"hello"` | `{key("hello"): "привет"}` | `"привет"`, `lt_translate` **не вызывается** |
| `"hello"` | `{}` | `lt_translate` вызывается, кэш пополняется |
| Кэш с fallback (`ok=False`) | `{}` | запись **не** попадёт в кэш |

#### 7.3. Батчинг

| Проверка | Ожидание |
|---|---|
| 5 коротких строк укладываются в `MAX_CHUNK` | один вызов `lt_translate` |
| 10 длинных строк не укладываются | несколько вызовов |
| Батч вернул разное число строк | срабатывает fallback — построчный перевод |
| Батч упал (`ok=False`) | fallback — построчный перевод |

#### 7.4. Help-строки

| Вход | Ожидание |
|---|---|
| `"  run    Run a command"` | prefix `"  run    "` не переводится, body `"Run a command"` переводится |
| `"  --flag <VALUE>    Description"` | то же самое |
| `"Обычный текст"` | кириллица → не переводится |
| `"hello"` (без отступов) | обычная обработка, не help-строка |

#### 7.5. Сохранение отступов

| Вход | Ожидание |
|---|---|
| `"    hello"` (4 пробела) | `"    привет"` — отступ сохранён |
| `"hello    "` (хвостовые) | `"привет    "` |
| `"\thello"` | `"\tпривет"` |
| Пустая строка внутри | остаётся как есть |

**Пример:**

```python
def test_process_uses_cache(mocker):
    mocker.patch("translate.lt_translate", return_value=("привет", True))
    cache = {translate.key("hello"): "привет"}
    out = translate.process("hello", cache)
    assert out == "привет"
    translate.lt_translate.assert_not_called()
```

---

### 8. `main()` — точка входа

**Назначение:** прочитать stdin, перевести, записать stdout, сохранить кэш.

Тестируется с `monkeypatch` для stdin и `capsys` для stdout.

**Случаи:**

| stdin | Ожидание |
|---|---|
| `""` | stdout пустой, кэш не пишется |
| `"   \n"` | то же |
| `"\ufeffhello"` (с BOM) | BOM отрезан, `hello` переведён |
| `"hello"` | stdout = перевод |
| `"hello\n"` | stdout = перевод + `\n` |
| Русский текст | пропускается, выводится как есть |

**Проверка побочных эффектов:**

- Кэш-файл создан после запуска.
- При ошибке API кэш **не** пополняется fallback-записями.

---

## Фикстуры (`conftest.py`)

Общие фикстуры для всех тестов.

### `temp_cache` — временный путь к кэшу

```python
@pytest.fixture
def temp_cache(tmp_path, monkeypatch):
    fake = tmp_path / "translate_ru.json"
    monkeypatch.setattr(translate, "CACHE_FILE", str(fake))
    return fake
```

Изолирует тесты от реального `~/.cache/`.

### `reset_flags` — сброс глобальных флагов

```python
@pytest.fixture(autouse=True)
def reset_flags():
    translate._api_warned = False
    translate._cache_warned = False
    yield
    translate._api_warned = False
    translate._cache_warned = False
```

`autouse=True` — применяется ко всем тестам. Гарантирует, что состояние не протекает между тестами.

### `mock_requests` — мок `requests.get`

```python
@pytest.fixture
def mock_requests(mocker):
    return mocker.patch("translate.requests.get")
```

Возвращает мок, каждый тест настраивает ответ по-своему.

---

## Категории тестов

### Быстрые (по умолчанию)

Без сети, без реальных файлов. Запускаются за доли секунды.

- `test_should_skip.py`
- `test_key.py`
- `test_cache.py` (с `tmp_path`)
- `test_quota.py` (с моком)
- `test_lt_translate.py` (с моком)
- `test_process.py` (с моком)
- `test_main.py` (с `monkeypatch`)

### Медленные (интеграционные)

Помечены `@pytest.mark.integration`. **Тратят квоту MyMemory**, требуют интернета.

Запускаются отдельно: `pytest -m integration`.

Не включаются в CI по умолчанию — иначе каждый push будет есть квоту.

---

## Маркеры pytest

В `pytest.ini` или `pyproject.toml`:

```ini
[pytest]
markers =
    integration: тесты, требующие реальный MyMemory API (медленно, тратит квоту)
```

Без регистрации маркеров pytest выдаёт warning о неизвестном маркере.

---

## Покрытие (coverage)

Цель — **85–90%**.

Запустить:

    pytest tests/ --cov=translate --cov-report=term-missing

Отчёт покажет **непокрытые строки** — что ещё стоит протестировать.

**Ожидаемо непокрытыми могут остаться:**

- ветки `except Exception` для экзотических ошибок (`MemoryError`, `KeyboardInterrupt`);
- код в `if __name__ == "__main__"` (выполняется только при прямом запуске);
- редкие ветки fallback.

Это нормально. **100%** обычно недостижимо без искусственных тестов.

---

## Что НЕ тестируется

1. **Реальный сетевой доступ** (кроме `@pytest.mark.integration`).
2. **Поведение MyMemory при разных языках** — это внешний сервис, не наш код.
3. **Логика zsh/PowerShell обёртки `ru`** — тестируется отдельно, если понадобится, через subprocess.
4. **Кодировка на разных ОС** — покрывается частично в `test_main.py`.

---

## Что делать, если тест падает

1. Запусти с `-v` — увидишь, какой именно ассерт не прошёл.
2. Запусти с `-x` — остановиться на первой ошибке.
3. Запусти с `-s` — показать stdout/stderr (полезно для `capsys`).
4. Запусти с `--pdb` — открыть отладчик в точке падения.

**Формат:**

    pytest tests/test_process.py::test_process_uses_cache -v -s --pdb

---

## Порядок написания

1. **`test_should_skip.py`** — самое простое, без моков.
2. **`test_key.py`** — тривиально.
3. **`test_cache.py`** — фикстура `tmp_path`.
4. **`test_quota.py`** — первый опыт с моками.
5. **`test_lt_translate.py`** — основная логика с моками.
6. **`test_process.py`** — самый важный файл, много параметризации.
7. **`test_main.py`** — end-to-end с `monkeypatch` и `capsys`.
8. **Интеграционные** — в самом конце, помечены `@pytest.mark.integration`.

---

## Дальнейшие шаги

После того как тесты работают локально:

1. **GitHub Actions** — автозапуск `pytest` при каждом push и pull request.
2. **Codecov / Coveralls** — измерение покрытия в CI.
3. **Badge в README** — «tests passing» и «coverage X%».
4. **Pre-commit hook** — автозапуск быстрых тестов перед коммитом.