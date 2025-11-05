#!/usr/bin/env python3
"""
Тестирование новой функциональности пакетного удаления отложенных рассылок.
"""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from db_session import get_db
from models.broadcast import ScheduledBroadcast
from models.crud import (
    create_scheduled_broadcast,
    delete_scheduled_messages,
    delete_scheduled_messages_by_admin,
    get_scheduled_broadcasts_by_admin
)


def test_bulk_delete_functionality():
    """
    Тестирует функциональность пакетного удаления отложенных рассылок.
    """
    print("=== Тестирование функциональности пакетного удаления ===")
    
    # Создаем тестовые данные
    admin_id = 123456789  # Тестовый ID администратора
    
    print(f"Создание тестовых рассылок для администратора {admin_id}...")
    
    with get_db() as db:
        # Удаляем все существующие тестовые рассылки для этого администратора
        existing_broadcasts = db.query(ScheduledBroadcast).filter(
            ScheduledBroadcast.admin_id == admin_id
        ).all()
        
        for broadcast in existing_broadcasts:
            db.delete(broadcast)
        db.commit()
        
        # Создаем 60 тестовых рассылок
        test_broadcasts = []
        for i in range(60):
            scheduled_time = datetime.now() + timedelta(days=i+1)
            message_content = f'{{"text": "Тестовое сообщение {i}", "message_id": {i+1}}}'
            
            broadcast = create_scheduled_broadcast(
                db=db,
                admin_id=admin_id,
                message_content=message_content,
                scheduled_datetime=scheduled_time
            )
            test_broadcasts.append(broadcast.id)
        
        print(f"Создано {len(test_broadcasts)} тестовых рассылок")
        
        # Проверяем, что рассылки созданы
        stored_broadcasts = get_scheduled_broadcasts_by_admin(db, admin_id)
        print(f"Проверка: в базе данных {len(stored_broadcasts)} рассылок")
        
        # Тестируем пакетное удаление конкретных ID
        ids_to_delete = test_broadcasts[:30]  # Удаляем первые 30
        print(f"Удаление {len(ids_to_delete)} рассылок через delete_scheduled_messages...")
        
        success_count, error_count, failed_ids = delete_scheduled_messages(db, ids_to_delete)
        print(f"Удаление по ID: успешно={success_count}, ошибок={error_count}, неудачные={failed_ids}")
        
        # Проверяем оставшиеся рассылки
        remaining_broadcasts = get_scheduled_broadcasts_by_admin(db, admin_id)
        print(f"После удаления по ID: осталось {len(remaining_broadcasts)} рассылок")
        
        # Тестируем удаление всех рассылок администратора
        print("Удаление всех оставшихся рассылок через delete_scheduled_messages_by_admin...")
        success_count, error_count, failed_ids = delete_scheduled_messages_by_admin(db, admin_id)
        print(f"Удаление всех: успешно={success_count}, ошибок={error_count}, неудачные={failed_ids}")
        
        # Проверяем, что все рассылки удалены
        final_broadcasts = get_scheduled_broadcasts_by_admin(db, admin_id)
        print(f"После удаления всех: осталось {len(final_broadcasts)} рассылок")
        
        if len(final_broadcasts) == 0:
            print("✅ Тест пройден успешно! Все рассылки были удалены.")
        else:
            print("❌ Тест не пройден! Не все рассылки были удалены.")
    
    print("=== Тестирование завершено ===")


if __name__ == "__main__":
    test_bulk_delete_functionality()