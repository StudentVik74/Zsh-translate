# Установка

## Windows (PowerShell)

### 1. Python

Скачай Python 3.10+ с [python.org](https://www.python.org/downloads/).
При установке поставь галочку **«Add Python to PATH»**.

Проверь:

```powershell
python --version
```

### 2. Библиотека requests

```powershell
python -m pip install requests
```

### 3. Скрипт

Создай папку:

```powershell
New-Item -ItemType Directory -Path "$HOME\.zsh" -Force
```

Скопируй `translate.py` в `$HOME\.zsh\`:

```powershell
Copy-Item "translate.py" "$HOME\.zsh\translate.py"
```

Проверь:

```powershell
Test-Path "$HOME\.zsh\translate.py"
# True
```

### 4. Политика выполнения

Один раз:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 5. Функция ru

Создай профиль (если ещё нет):

```powershell
if (!(Test-Path -Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force }
```

Открой:

```powershell
notepad $PROFILE
```

Вставь содержимое `Scripts/ru-shell.ps1`. **Сохрани как UTF-8**
(Файл → Сохранить как → Кодировка: UTF-8).

### 6. Активация

Закрой и открой PowerShell заново, или:

```powershell
. $PROFILE
```

### 7. Проверка

```powershell
ru
ru -t "hello"
echo "test" | ru
```

