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

Вставь содержимое `PowerShell/profile.ps1`. **Сохрани как UTF-8**
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
ru ipconfig
echo "test" | ru
```

## Linux / macOS (zsh)

### 1. requests

```bash
pip3 install --user --break-system-packages requests
```

На старых системах может хватить:

```bash
pip3 install --user requests
```

### 2. Скрипт

```bash
mkdir -p ~/.zsh
cp translate.py ~/.zsh/translate.py
chmod +x ~/.zsh/translate.py
```

### 3. Функция ru

Добавь содержимое `linux/zshrc-snippet.sh` в `~/.zshrc`:

```bash
cat linux/zshrc-snippet.sh >> ~/.zshrc
```

Или вручную открой `nano ~/.zshrc` и добавь функцию.

### 4. Активация

```bash
source ~/.zshrc
```

### 5. Проверка

```bash
ru
ru -t "hello"
ru ls -la /nonexistent
echo "test" | ru
```