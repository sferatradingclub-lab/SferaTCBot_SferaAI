# Быстрое развертывание фикса на сервер

## Команды для SSH (копируй и вставляй):

```bash
# 1. Перейти в проект
cd ~/sferatc-testbot

# 2. Остановить агента
sudo systemctl stop sfera-agent

# 3. Обновить код
git pull origin main

# 4. Запустить агента
sudo systemctl start sfera-agent

# 5. Проверить статус
sudo systemctl status sfera-agent
```

## Если агент запустился (active running):
✅ Готово! Проверь в Telegram Mini App.

## Если агент failed:
```bash
# Показать последние 50 строк логов
sudo journalctl -u sfera-agent -n 50 --no-pager
```

Скопируй ошибку и пришли мне.

---

**Что исправлено:**
- Увеличен timeout инициализации с 10 до 30 секунд
- Процесс теперь успеет загрузить Qdrant + Redis + embeddings
