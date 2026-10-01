# translate-terminal

Переводчик вывода терминала на русский язык. Работает в **zsh** (Linux/macOS) и **PowerShell** (Windows).

Переводит stdout и stderr любой команды через [MyMemory API](https://mymemory.translated.net/). Не требует Docker, не грузит процессор, работает на слабом железе.

## Возможности

- **Три режима:**
  - `ru <команда>` — выполнить команду и перевести вывод
  - `ru -t <текст>` — перевести текст
  - `<команда> | ru` — перевести stdin
- **Кэш успешных переводов** — повторные запуски мгновенны
- **Фильтр кириллицы** — русские строки не идут в переводчик
- **Батчинг** — несколько строк за один запрос
- **Help-режим** — не переводит имена команд в выводе `--help`
- **Проверка квоты** — сообщает, если лимит MyMemory исчерпан

## Установка

### Windows (PowerShell)

Подробно: [INSTALL.md](INSTALL.md#windows)

Кратко:

1. Установи Python 3.10+ с [python.org](https://www.python.org/downloads/) (галочка «Add to PATH»).
2. Установи `requests`:
   ```
   python -m pip install requests
   ```
3. Создай папку и скопируй скрипт:
   ```powershell
   New-Item -ItemType Directory -Path "$HOME\.zsh" -Force
   Copy-Item "translate.py" "$HOME\.zsh\translate.py"
   ```
4. Разреши выполнение скриптов (один раз):
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
5. Добавь функцию `ru` в профиль PowerShell (см. `windows/profile.ps1`).
6. Перезапусти PowerShell и проверь:
   ```powershell
   ru -t "hello"
   ```

### Linux / macOS (zsh)

Кратко:

1. Установи `requests`:
   ```bash
   pip3 install --user --break-system-packages requests
   ```
2. Скопируй скрипт:
   ```bash
   mkdir -p ~/.zsh
   cp translate.py ~/.zsh/translate.py
   ```
3. Добавь функцию `ru` в `~/.zshrc` (см. `linux/zshrc-snippet.sh`).
4. Перезагрузи конфиг:
   ```bash
   source ~/.zshrc
   ```
5. Проверь:
   ```bash
   ru -t "hello"
   ```

## Использование

```bash
ru ls -la /nonexistent
ru git status
ru docker --help
ru -t "hello"
echo "Something went wrong" | ru
```

## Настройка

### Email для MyMemory

Открой `translate.py` и найди:

```python
MYMEMORY_EMAIL = ""
```

Впиши свой email — лимит поднимется с 5000 до 50000 символов в день. Регистрация не нужна.

### Кэш

Переводы сохраняются в `~/.cache/translate_ru/translate_ru.json` (Linux) или `%USERPROFILE%\.cache\translate_ru\translate_ru.json` (Windows).

Сбросить:

```bash
rm -f ~/.cache/translate_ru/translate_ru.json
```

```powershell
Remove-Item "$HOME\.cache\translate_ru\translate_ru.json"
```

## Ограничения

- Только **en → ru**. Другие языки не переводятся.
- **Лимит MyMemory:** 5000 символов/день анонимно, 50000 с email.
- **Приватность:** текст уходит на сервер MyMemory. Не используй для паролей и секретов.
- **Нет цветного вывода** — ANSI-коды не восстанавливаются.

## Лицензия

[MIT](LICENSE)