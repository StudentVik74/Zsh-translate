# Решение проблем

## Windows

### Кракозябры вместо русского (`ÐŸÑ€Ð¸Ð²ÐµÑ‚`)

Проверь, что в профиле (`$PROFILE`) есть **обе** строки:

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

Если файл редактировался в Блокноте, проверь кодировку:

```powershell
Get-Content $PROFILE -Encoding UTF8 | Select-Object -First 3
```

Если вместо русского — мусор, файл сохранён не в UTF-8. Пересохрани через PowerShell:

```powershell
$content = Get-Content $PROFILE -Encoding Default -Raw
Set-Content -Path $PROFILE -Value $content -Encoding UTF8
```

### `ru: The term 'ru' is not recognized`

Профиль не загрузился. Проверь:

```powershell
Test-Path $PROFILE
```

Если `False` — создай:

```powershell
if (!(Test-Path -Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force }
notepad $PROFILE
```

### `ModuleNotFoundError: No module named 'requests'`

Установи в тот Python, который запускает скрипт:

```powershell
python -m pip install requests
```

### `can't open file 'C:\Users\<Имя>\.zsh\translate.py'`

Скрипт не на месте. Проверь:

```powershell
Test-Path "$HOME\.zsh\translate.py"
```

Если `False` — скопируй:

```powershell
Copy-Item "translate.py" "$HOME\.zsh\translate.py"
```

### `ru << команда >>` выдаёт «нераспознанная командная строка»

Старая версия функции. Обнови профиль — блок команды должен быть:

```powershell
$cmd = $args[0]
if ($args.Count -gt 1) {
    $cmdArgs = $args[1..($args.Count-1)]
    & $cmd @cmdArgs 2>&1 | python "$HOME\.zsh\translate.py"
} else {
    & $cmd 2>&1 | python "$HOME\.zsh\translate.py"
}
```

## Linux / macOS

### `pip: command not found`

Используй `pip3` или `python3 -m pip`:

```bash
python3 -m pip install --user --break-system-packages requests
```

### `error: externally-managed-environment`

Ubuntu 23.04+ и Debian 12+ защищают системный Python. Обход:

```bash
pip3 install --user --break-system-packages requests
```

### `python3: can't open file 'translate.py'`

Неверный путь. Скрипт лежит в `~/.zsh/translate.py`:

```bash
python3 ~/.zsh/translate.py
```

### `ru: command not found` после добавления функции

Не перезагружен `.zshrc`:

```bash
source ~/.zshrc
```

### Лимит MyMemory исчерпан

Проверь квоту:

```bash
curl -sS "https://api.mymemory.translated.net/get?q=test&langpair=en|ru" \
  | python3 -m json.tool | grep -E "quotaFinished|responseStatus"
```

Если `quotaFinished: true` — добавь email в `MYMEMORY_EMAIL` в `translate.py`.
