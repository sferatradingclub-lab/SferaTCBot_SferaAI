# Обновление кода на сервере

## Шаг 1: Подключиться к серверу

```bash
ssh user@your-server
```

## Шаг 2: Перейти в директорию проекта

```bash
cd /path/to/SferaTC-Bot-Sfera-AI  # Укажите свой путь
```

## Шаг 3: Остановить сервисы

```bash
sudo systemctl stop sferatc-bot sfera-agent
```

## Шаг 4: Проверить текущее состояние

```bash
git status
```

Если увидите `SferaAI_2 (modified content)` - значит там вложенный репозиторий.

## Шаг 5: Удалить вложенный .git (если есть)

```bash
# Проверить наличие
ls -la SferaAI_2/.git

# Если есть - удалить
rm -rf SferaAI_2/.git
```

## Шаг 6: Сбросить локальные изменения (если нужно)

```bash
# ВНИМАНИЕ: Это удалит все локальные изменения!
git reset --hard HEAD
git clean -fd
```

## Шаг 7: Обновить код с GitHub

```bash
git pull origin main
```

## Шаг 8: Проверить что получили

```bash
git log -1 --oneline
# Должно показать: 0e4aded feat: merge SferaAI_2 into main repository

git status
# Должно показать: working tree clean
```

## Шаг 9: Обновить зависимости (если нужно)

```bash
# Основные зависимости
source venv/bin/activate  # или откуда у вас venv
pip install -r requirements.txt

# SferaAI_2 зависимости
cd SferaAI_2
pip install -r requirements.txt
cd ..
```

## Шаг 10: Запустить сервисы

```bash
sudo systemctl start sferatc-bot sfera-agent
sudo systemctl status sferatc-bot
sudo systemctl status sfera-agent
```

## Шаг 11: Проверить логи

```bash
# В реальном времени
sudo journalctl -u sferatc-bot -f
# Ctrl+C чтобы выйти

sudo journalctl -u sfera-agent -f
```

---

## Если что-то пошло не так

### Вернуться к предыдущей версии:
```bash
git log --oneline  # Найти хеш нужного коммита
git reset --hard <commit-hash>
sudo systemctl restart sferatc-bot sfera-agent
```

### Проверить конфликты:
```bash
git status
git diff
```

### Принудительно синхронизировать с GitHub:
```bash
git fetch origin
git reset --hard origin/main
```

---

## Быстрая команда (всё сразу)

```bash
# ВНИМАНИЕ: Использовать только если уверены!
cd /path/to/project && \
sudo systemctl stop sferatc-bot sfera-agent && \
rm -rf SferaAI_2/.git && \
git reset --hard HEAD && \
git pull origin main && \
sudo systemctl start sferatc-bot sfera-agent && \
sudo systemctl status sferatc-bot sfera-agent
```

---

## Проверка успеха

```bash
# 1. Проверить версию
git log -1 --oneline
# Ожидается: 0e4aded feat: merge SferaAI_2 into main repository

# 2. Проверить что SferaAI_2 теперь часть основного репо
git ls-files SferaAI_2 | head -5
# Должно показать файлы из SferaAI_2

# 3. Проверить что нет вложенного .git
ls -la SferaAI_2/.git
# Должно: No such file or directory

# 4. Проверить что сервисы работают
sudo systemctl is-active sferatc-bot
sudo systemctl is-active sfera-agent
# Оба должны показать: active
```
