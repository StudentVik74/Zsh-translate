## Офлайн-режим (Docker)

По умолчанию `translate.py` использует **MyMemory API** — внешний сервис
через интернет. Это просто, но имеет ограничения: дневная квота
(5000 символов анонимно), зависимость от сети и отправка текста на
чужой сервер.

Если у вас **достаточно мощное железо**, можно поднять **локальный
переводчик в Docker**. Он работает офлайн, без лимитов и без интернета.

### Когда стоит переходить

| Ситуация | Онлайн (MyMemory) | Офлайн (Docker) |
|---|---|---|
| Слабое железо | ✅ Лучший выбор | ❌ Контейнер не потянет |
| Хороший CPU (4+ ядра) | ⚠️ Работает, но квота | ✅ Лучший выбор |
| Большие объёмы перевода | ❌ Квота 50k символов/день | ✅ Без лимитов |
| Конфиденциальные данные | ❌ Уходят на сервер | ✅ Локально |
| Нет интернета | ❌ Не работает | ✅ Работает |

### Требования

- **Docker** (Desktop для Windows/macOS, `docker.io` для Linux)
- **RAM**: 4 ГБ минимум, 8+ ГБ рекомендуется
- **Место на диске**: ~2 ГБ под образ

### Быстрый старт

**1. Запустить контейнер через Docker Compose:**

```bash
docker compose up -d
```


**2. Проверить, что сервер работает:**

```bash
curl -sS http://localhost:5000/translate \
  -H "Content-Type: application/json" \
  -d '{"q":"Hello, World!","source":"en","target":"ru"}'
```

Ожидаемый ответ:

```json
{"translatedText":"Привет, Мир!"}
```

**3. Переключить `translate.py` на локальный сервер.**

Открой `utils/translate.py` и измени две вещи.

**Константа URL:**

```python
LT_URL = "http://localhost:5000/translate"
```

**Формат запроса в `lt_translate` — с GET на POST:**

```python
def lt_translate(text: str, source: str = "en", target: str = "ru"):
    """Перевести текст через локальный LibreTranslate."""
    text = ANSI_RE.sub('', text)
    try:
        r = requests.post(
            LT_URL,
            json={"q": text, "source": source, "target": target},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["translatedText"], True
    except Exception as e:
        notify_first_failure(e)
        return text, False
```

**4. Готово.** Все команды `ru` теперь работают через локальный сервер:

```bash
ru ls -la /nonexistent
ru docker --help
echo "Something went wrong" | ru
```

### Управление контейнером

| Команда | Что делает |
|---|---|
| `docker compose up -d` | Запустить в фоне |
| `docker compose down` | Остановить и удалить контейнер |
| `docker compose logs -f` | Смотреть логи |
| `docker compose restart` | Перезапустить |
| `docker ps --filter name=libretranslate` | Проверить статус |

Автозапуск после перезагрузки системы обеспечивается флагом
`restart: unless-stopped` в `docker-compose.yml`.

### Типичные проблемы

- **`Cannot connect to the Docker daemon`** — Docker не запущен.
  Linux: `sudo systemctl start docker`. Windows/macOS: откройте
  Docker Desktop.
- **`port is already allocated`** — порт 5000 занят. Поменяйте
  проброс на `5001:5000` в `docker-compose.yml` и обновите `LT_URL`.
- **`Restarting (132)`** — контейнер требует AVX2, которого нет на CPU.
  Вернитесь к онлайн-режиму.
- **100% CPU на старте** — нормально первые 10–30 секунд (загрузка
  моделей). Если держится постоянно — вернитесь к онлайн-режиму.

---
