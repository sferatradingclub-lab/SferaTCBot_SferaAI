#!/usr/bin/env python3
"""
Скрипт миграции: TinyDB (ltm.json) → Qdrant (через UnifiedUserState)
Запустите ОДИН РАЗ перед развертыванием новой версии.

Использование:
    python scripts/migrate_ltm_to_qdrant.py
"""
import os
import sys
import asyncio
import json
from pathlib import Path

# Добавить родительскую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from tinydb import TinyDB
from unified_user_state import get_unified_instance
from dotenv import load_dotenv

load_dotenv()

LTM_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'ltm.json')


async def migrate():
    """Мигрировать все данные пользователей из TinyDB в UnifiedUserState (Qdrant)"""
    
    print("\n" + "="*70)
    print("  МИГРАЦИЯ ДАННЫХ: TinyDB → Qdrant")
    print("="*70 + "\n")
    
    if not os.path.exists(LTM_DB_PATH):
        print(f"❌ ltm.json не найден в {LTM_DB_PATH}")
        print("Нечего мигрировать.")
        return
    
    # Загрузить TinyDB
    print(f"📂 Загрузка данных из {LTM_DB_PATH}...")
    db = TinyDB(LTM_DB_PATH)
    users_table = db.table('users')
    all_users = users_table.all()
    
    if not all_users:
        print("ℹ️  Пользователи не найдены в ltm.json")
        print("Нечего мигрировать.")
        return
    
    print(f"✅ Найдено {len(all_users)} пользователей для миграции\n")
    
    # Инициализировать UnifiedUserState
    print("🔗 Подключение к Qdrant...")
    unified_state = get_unified_instance()
    
    # Мигрировать каждого пользователя
    migrated_count = 0
    failed_count = 0
    
    print("\n" + "-"*70)
    print("  СТАТУС МИГРАЦИИ")
    print("-"*70 + "\n")
    
    for i, user in enumerate(all_users, 1):
        user_id = user.get('user_id')
        if not user_id:
            print(f"⚠️  [{i}/{len(all_users)}] Пропуск пользователя без user_id: {user}")
            failed_count += 1
            continue
        
        try:
            # Обновить состояние пользователя в Qdrant
            await unified_state.update_user_state(user_id, user)
            print(f"✅ [{i}/{len(all_users)}] Мигрирован: {user_id}")
            
            # Показать детали
            if user.get('name'):
                print(f"    └─ Имя: {user.get('name')}")
            if user.get('active_plan'):
                print(f"    └─ План: {user.get('active_plan')}")
            
            migrated_count += 1
            
        except Exception as e:
            print(f"❌ [{i}/{len(all_users)}] Ошибка при миграции {user_id}: {e}")
            failed_count += 1
    
    # Итоговая статистика
    print("\n" + "="*70)
    print("  ИТОГО")
    print("="*70)
    print(f"✅ Успешно мигрировано: {migrated_count}")
    print(f"❌ Ошибок: {failed_count}")
    print(f"📊 Всего обработано: {len(all_users)}")
    print("="*70 + "\n")
    
    if migrated_count == len(all_users):
        print("🎉 Миграция завершена УСПЕШНО!")
    elif migrated_count > 0:
        print("⚠️  Миграция завершена с ошибками. Проверьте логи выше.")
    else:
        print("❌ Миграция не удалась!")
        return
    
    # Инструкции по резервному копированию
    print("\n" + "-"*70)
    print("  ВАЖНО: РЕЗЕРВНОЕ КОПИРОВАНИЕ")
    print("-"*70)
    print("\n⚠️  НЕ УДАЛЯЙТЕ ltm.json сразу!")
    print("1. Сначала создайте резервную копию:")
    print(f"   cp {LTM_DB_PATH} {LTM_DB_PATH}.backup")
    print("\n2. Протестируйте новую версию с Qdrant:")
    print("   python agent.py dev")
    print("\n3. Убедитесь, что все работает корректно")
    print("\n4. Только после этого можете удалить старый файл")
    print("-"*70 + "\n")


if __name__ == '__main__':
    asyncio.run(migrate())
