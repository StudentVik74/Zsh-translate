# Офлайн-перевод через Docker

По умолчанию `translate.py` использует MyMemory API — внешний сервис
через интернет. Это удобно когда слабое железо, но имеет ограничения: дневная квота,
зависимость от сети, отправка текста на чужой сервер.

Если у вас достаточно хорошее железо, можно поднять локальный
переводчик в Docker — он работает офлайн, без лимитов и без интернета.

---


Короткое правило
- Слабое железо, редкие команды → онлайн
- Хорошее железо, регулярное использование → офлайн

---

## Что понадобится

### Железо

| Параметр           | Минимум  | Рекомендуется |
|--------------------|----------|---|
| CPU                | 4+ ядер  |
| RAM                | 8+ ГБ    |
| Свободное место    |  5+ ГБ   |

---

## Выбор образа

### Вариант 1. LibreTranslate с готовыми моделями 

Образ: `dvurechensky/libretranslate-offline-ru-en-zh`

- Модели `en-ru` и `ru-zh` уже внутри образа.
- Не требует интернета после скачивания.
- Совместим с API LibreTranslate
- Запускается быстро

Плюсы: простота, готовность, совместимость с текущим скриптом.

Минусы: только три языка(русский, английский, китайский)

### Вариант 2. Официальный LibreTranslate

Образ: `libretranslate/libretranslate:latest`

- Поддерживает 50+ языков.
- Требует сборки с `--build-arg with_models=true` для офлайн-режима.
- Иначе модели скачиваются при первом запросе.

Плюсы: максимум языков.

Минусы: тяжелее.

---

## Быстрый старт с LibreTranslate

Это самый простой путь. Все команды выполняются **один раз**.

### 1. Скачать образ

```bash
docker pull dvurechensky/libretranslate-offline-ru-en-zh:latest
```

Размер: ~1.5 ГБ. Займёт несколько минут.

### 2. Запустить контейнер

```bash
docker run -d \
  --name libretranslate \
  --restart unless-stopped \
  -p 5000:5000 \
  -e LT_HOST=0.0.0.0 \
  dvurechensky/libretranslate-offline-ru-en-zh
```

Разбор флагов:
- `-d` — в фоне (не блокирует терминал).
- `--name libretranslate` — имя для дальнейшего управления.
- `--restart unless-stopped` — автозапуск после перезагрузки системы.
- `-p 5000:5000` — порт 5000 на хосте и в контейнере.
- `-e LT_HOST=0.0.0.0` — слушать все интерфейсы (иначе снаружи не достучаться).

### 3. Проверить, что сервер работает

Подожди 10–15 секунд и выполни:

```bash
curl -sS http://localhost:5000/translate \
  -H "Content-Type: application/json" \
  -d '{"q":"Hello, World!","source":"en","target":"ru"}'
```

Ожидаемо:

```json
{"translatedText":"Привет, Мир!"}
```

Если увидел `Привет, Мир!` — сервер работает.

### 4. Подключить к `translate.py`

Открой `utils/translate.py` и измени две вещи.

Константа URL:

```python
LT_URL = "http://localhost:5000/translate"
```

Формат запроса в функции `lt_translate`:

Сейчас скрипт использует GET-запрос к MyMemory. LibreTranslate
принимает POST с JSON. Замени тело функции:

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
        data = r.json()
        return data["translatedText"], True
    except Exception as e:
        notify_first_failure(e)
        return text, False
```

Функция `check_quota()` для LibreTranslate не нужна — у него нет
дневной квоты. Удали вызов или оставь заглушку.

### 5. Проверить

```bash
echo "Hello, World! This is a test." | python3 utils/translate.py
```

Ожидаемо:

```
Привет, Мир! Это тест.
```

---

## Автозапуск и обслуживание

### Контейнер запускается сам

Благодаря `--restart unless-stopped`, контейнер поднимется:
- после перезагрузки системы;
- после падения;
- после `systemctl restart docker`.

Но не поднимется, если ты сам остановил его через `docker stop`.

### Проверить статус

```bash
docker ps --filter name=libretranslate
```

Должен быть `Up X minutes`.

### Посмотреть логи

```bash
docker logs --tail 30 libretranslate
```

Ищи строку `Listening at: http://0.0.0.0:5000` — сервер готов.

### Остановить / запустить

```bash
docker stop libretranslate
docker start libretranslate
```

### Обновить образ

```bash
docker pull dvurechensky/libretranslate-offline-ru-en-zh:latest
docker stop libretranslate
docker rm libretranslate
# заново docker run (команда выше)
```

### Удалить всё

```bash
docker stop libretranslate
docker rm libretranslate
docker rmi dvurechensky/libretranslate-offline-ru-en-zh
```

---

##  Проблемы

Порт 5000 занят другим приложением. Проверь:

```bash
# Linux/macOS
sudo ss -tlnp | grep 5000
```

```powershell
# Windows
netstat -ano | findstr :5000
```

Решение — использовать другой порт снаружи:

```bash
docker run -d ... -p 5001:5000 ...
```

И в `translate.py`:

```python
LT_URL = "http://localhost:5001/translate"
```

### `Empty reply from server`

Контейнер ещё грузит модели. Подожди 30–60 секунд и проверь снова.

Если через минуту всё равно пусто:

```bash
docker logs libretranslate
```

Ищи ошибки в логах.

### `Restarting (132)`

Ошибка `SIGILL` — контейнер требует инструкции, которых нет на CPU.
Скорее всего, нужен AVX2, а его нет.

Решение: вернуться к онлайн-режиму.

### Контейнер ест 100% CPU

Первые 10–30 секунд после старта — норма (загрузка моделей).
Если 100% держится постоянно — контейнер перегружен, вернись к онлайн.

### Медленно работает

Возможные причины:
- Мало RAM 
- Модели грузятся при каждом запросе (нет кеша).
- Одновременные запросы конкурируют за CPU.

Проверка ресурсов:

```bash
docker stats libretranslate
```

---

## Гибридный режим 

Можно совместить: сначала пробовать офлайн, при неудаче — онлайн.

```python
PROVIDERS = [
    "http://localhost:5000/translate",         # офлайн
    "https://api.mymemory.translated.net/get",  # онлайн
]

def lt_translate(text, source="en", target="ru"):
    for url in PROVIDERS:
        try:
            # попытка через url
            ...
            return result, True
        except Exception:
            continue
    return text, False
```

Плюсы: лучший из двух миров.
Минусы: сложнее код, надо тестировать оба пути.

В текущей версии `translate.py` не реализовано — только идея.

---

## Полезные ссылки

- [LibreTranslate на Docker Hub](https://hub.docker.com/r/libretranslate/libretranslate)
- [Community-образ с моделями ru/en/zh](https://hub.docker.com/r/dvurechensky/libretranslate-offline-ru-en-zh)
- [LibreTranslate API docs](https://libretranslate.com/docs/)
- [Проверка AVX2 в Linux](https://unix.stackexchange.com/questions/261836/how-to-check-if-cpu-supports-avx2)

---

Если железо позволяет — офлайн-режим даёт полную свободу: без квот,
без интернета, без утечки данных. Если нет — онлайн остаётся надёжным
и простым вариантом.