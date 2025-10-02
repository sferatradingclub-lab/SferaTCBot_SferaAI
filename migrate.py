import pickle
from datetime import datetime

# Импортируем наши модели и сессию для работы с новой БД
from models.base import Base, engine
from models.user import User
from db_session import SessionLocal

print("--- Начало миграции данных ---")

# Шаг 1: Создаем таблицы в новой базе данных, если их еще нет
try:
    print("1. Создание таблиц в PostgreSQL...")
    Base.metadata.create_all(bind=engine)
    print("   ...Таблицы успешно созданы (или уже существовали).")
except Exception as e:
    print(f"   !!! Ошибка при создании таблиц: {e}")
    exit()

# Шаг 2: Загружаем данные из старого файла .pickle
try:
    print("2. Загрузка данных из bot_data.pickle...")
    with open('bot_data.pickle', 'rb') as f:
        data = pickle.load(f)
    user_data = data.get('user_data', {})
    if not user_data:
        print("   !!! Файл bot_data.pickle пуст или не содержит данных пользователей. Миграция завершена.")
        exit()
    print(f"   ...Найдено {len(user_data)} пользователей для миграции.")
except FileNotFoundError:
    print("   !!! Файл bot_data.pickle не найден. Нечего мигрировать.")
    exit()
except Exception as e:
    print(f"   !!! Ошибка при чтении файла pickle: {e}")
    exit()


# Шаг 3: Переносим данные в новую базу
db = SessionLocal()
print("3. Начало переноса пользователей в PostgreSQL...")
migrated_count = 0
skipped_count = 0

for user_id, user_info in user_data.items():
    try:
        # Проверяем, нет ли уже такого пользователя в БД
        existing_user = db.query(User).filter(User.user_id == user_id).first()
        if existing_user:
            print(f"   - Пользователь с ID {user_id} уже существует. Пропускаем.")
            skipped_count += 1
            continue

        # Создаем нового пользователя на основе старых данных
        new_user = User(
            user_id=user_id,
            username=user_info.get('username'),
            full_name=user_info.get('full_name'),
            first_seen=user_info.get('first_seen', datetime.now()),
            last_seen=user_info.get('last_seen', datetime.now()),
            is_approved=user_info.get('is_approved', False),
            is_banned=user_info.get('is_banned', False),
            awaiting_verification=user_info.get('awaiting_verification', False),
            approval_date=user_info.get('approval_date') # Будет None, если ключа нет
        )
        db.add(new_user)
        print(f"   - Пользователь {user_id} ({user_info.get('username')}) подготовлен к добавлению.")
        migrated_count += 1
    except Exception as e:
        print(f"   !!! Не удалось обработать пользователя {user_id}. Ошибка: {e}")

try:
    db.commit()
    print("   ...Все новые пользователи успешно сохранены в базе данных.")
except Exception as e:
    print(f"   !!! Критическая ошибка при сохранении данных в БД: {e}")
    db.rollback()
finally:
    db.close()

print("\n--- Миграция завершена! ---")
print(f"Успешно перенесено: {migrated_count}")
print(f"Пропущено (уже существовали): {skipped_count}")