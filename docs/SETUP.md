# Запуск LectureBot с нуля

Проверено на CachyOS (Arch Linux), Python 3.14. Команды для macOS и Windows взяты из описания проекта, их должен проверить участник с этой системой.

## 1. Программы

Arch / CachyOS:
```bash
sudo pacman -S --needed git python github-cli
```
Ubuntu / Debian:
```bash
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip gh
```
macOS (сначала поставить [Homebrew](https://brew.sh)):
```bash
brew install git python gh
```
Windows (PowerShell), после установки закрыть и открыть PowerShell заново:
```powershell
winget install Git.Git
winget install Python.Python.3.12
winget install GitHub.cli
```
Проверка: `git --version` и `python --version` (на macOS `python3 --version`). Нужен Python 3.11 или новее.

## 2. Репозиторий

Одинаково на всех системах:
```bash
gh auth login
gh repo clone am1ani1m000/lecture-bot
cd lecture-bot
```
При `gh auth login` выбрать GitHub.com, HTTPS и вход через браузер. Проверка: `gh auth status`.

## 3. Окружение Python

Linux и macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate        # bash или zsh (на macOS по умолчанию zsh)
source .venv/bin/activate.fish   # fish (по умолчанию в CachyOS)
```
Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\activate
```
Если Windows пишет, что выполнение скриптов запрещено, один раз выполни `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` и повтори.

В начале строки появится `(.venv)`. Окружение включаем в каждом новом терминале.

Только Linux: `pip` по умолчанию ставит torch с библиотеками NVIDIA (несколько ГБ). Если видеокарта не нужна, сначала поставь облегчённый вариант:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```
Затем на любой системе:
```bash
pip install -r requirements.txt
```
## 4. Файл .env

Секреты хранятся только в `.env`. Он есть в `.gitignore` и никогда не попадает в git.

```bash
cp .env.example .env        # Windows: copy .env.example .env
nano .env                   # или code .env
```
Заполнить:
- `BOT_TOKEN`: токен тестового бота, его присылает участник 2 в личку.
- `LLM_API_KEY`: свой бесплатный ключ с openrouter.ai (Settings, Keys, Create Key).
- `LLM_BASE_URL=https://openrouter.ai/api/v1`
- `LLM_MODEL=openrouter/free`
- `EMBED_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

Значения пишем без кавычек и пробелов. Ключи никому не пересылаем и не вставляем в чат с ИИ.

## 5. Проверка

```bash
python scripts/test_llm.py
```
Должен напечататься ответ модели.

```bash
python bot.py
```
Написать тестовому боту `/start`, он должен ответить. Остановить бота: Ctrl+C.

## 6. Частые ошибки

| Ошибка | Что делать |
|---|---|
| `command not found: python` | Не включено `.venv` или нужно писать `python3` |
| В fish не работает `source .venv/bin/activate` | Использовать `source .venv/bin/activate.fish` |
| `ModuleNotFoundError` | Включить `.venv` и выполнить `pip install -r requirements.txt` |
| `pip install` идёт долго и качает `nvidia-*` | Так ставится torch с поддержкой видеокарты, см. совет в разделе 3 |
| `Missing credentials` | Нет `.env` или пустой `LLM_API_KEY` |
| `401` | Неверный ключ: вставлен не целиком или с пробелами |
| `429` | Бесплатная модель перегружена или кончился дневной лимит, подождать минуту |
| В `git status` виден `.env` | Остановиться и проверить `.gitignore` |
