# proactive_scheduler.py
import asyncio
import logging
from datetime import datetime, timedelta

from unified_user_state import get_unified_instance
from session_registry_redis import get_session_registry

# --- Конфигурация ---
CHECK_INTERVAL_SECONDS = 300  # 5 минут

async def run_proactive_scheduler():
    """
    Фоновый процесс, который периодически проверяет LTM на наличие пользователей,
    требующих проактивного вмешательства (follow-up по плану).
    """
    logging.info("🚀 Проактивный планировщик запущен.")
    unified_state = get_unified_instance()

    while True:
        try:
            logging.info("Планировщик: проверка активных планов...")
            active_users = await unified_state.get_all_active_users()

            if not active_users:
                logging.info("Планировщик: активных планов не найдено.")
            else:
                logging.info(f"Планировщик: найдено {len(active_users)} пользователей с активными планами.")
                for user_state in active_users:
                    user_id = user_state.get('user_id')
                    plan = user_state.get('active_plan')
                    last_update_str = user_state.get('last_update')
                    last_proactive_str = user_state.get('last_proactive_message')
                    
                    # Простая логика для начала: проверяем, если с последнего обновления прошел день
                    needs_follow_up = False
                    if last_update_str:
                        last_update_time = datetime.fromisoformat(last_update_str)
                        if datetime.now() - last_update_time > timedelta(days=1):
                            needs_follow_up = True
                    else:
                        # Если last_update нет, но план есть - значит, это первый follow-up
                        needs_follow_up = True
                    
                    # Не отправляем сообщения слишком часто (не чаще раза в день)
                    if last_proactive_str:
                        last_proactive_time = datetime.fromisoformat(last_proactive_str)
                        if datetime.now() - last_proactive_time < timedelta(days=1):
                            needs_follow_up = False

                    if needs_follow_up:
                        logging.info(f"❗️ Пользователю '{user_id}' требуется follow-up по плану '{plan}'.")
                        
                        # =================================================================
                        # PROACTIVE MESSAGING IMPLEMENTATION
                        # =================================================================
                        try:
                            # Get session registry
                            session_registry = get_session_registry()
                            
                            # Check if user has an active session
                            if await session_registry.is_active(user_id):
                                # User is online - send proactive message via agent
                                # Note: We can't easily get agent instance from Redis,
                                # so for now we just log. In future, implement message queue.
                                logging.info(f"📧 User {user_id} is online, but agent instance not accessible from scheduler")
                                logging.info("(Future: implement message queue for proactive messages)")
                                
                                # Update timestamp to avoid spam
                                await unified_state.update_user_state(user_id, {
                                    'last_proactive_message': datetime.now().isoformat(),
                                })
                            else:
                                # User is offline - log for future notification (email/SMS/push)
                                followup_message = f"""Привет! Это Sfera AI.
                                
Я заметила, что у тебя активен план '{plan}'.
Прошло уже 24 часа с последнего обновления.

Когда будешь готов, давай продолжим работу!
Просто открой приложение, и я сразу подключусь к тебе."""
                                
                                logging.info(f"📧 PROACTIVE MESSAGE для offline пользователя {user_id}:")
                                logging.info(followup_message)
                                logging.info("(В будущем: отправка email/SMS/push notification)")
                                
                                # Update timestamp anyway to avoid spam
                                await unified_state.update_user_state(user_id, {
                                    'last_proactive_message': datetime.now().isoformat(),
                                })
                            
                        except Exception as e:
                            logging.error(f"Ошибка при отправке проактивного сообщения {user_id}: {e}")

        except Exception as e:
            logging.error(f"Ошибка в цикле планировщика: {e}")

        # Пауза перед следующей проверкой
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)

async def test_scheduler_logic():
    """
    Выполняет один цикл проверки планировщика для тестирования.
    """
    logging.info("--- Запуск однократной проверки планировщика ---")
    unified_state = get_unified_instance()
    active_users = await unified_state.get_all_active_users()


    found_test_user = False
    if not active_users:
        logging.error("Тест провален: активных планов не найдено, хотя должен был быть.")
    else:
        logging.info(f"Найдено {len(active_users)} пользователей с активными планами.")
        for user_state in active_users:
            user_id = user_state.get('user_id')
            if user_id == "test_user_for_scheduler":
                found_test_user = True
                logging.info(f"✅ Успех: Тестовый пользователь '{user_id}' найден в списке активных.")
    
    if not found_test_user:
        logging.error(f"Тест провален: тестовый пользователь не был найден в списке активных. {active_users}")




async def main_test():
    """Async test main function"""
    unified_state = get_unified_instance()
    test_user_id = "test_user_for_scheduler"
    
    print("--- Тестирование Proactive Scheduler ---")
    
    # 1. Настройка тестового пользователя
    await unified_state.update_user_state(test_user_id, {
        'active_plan': '3-Day-Recovery',
        'plan_step': 1,
    })
    print(f"1. Создан тестовый пользователь '{test_user_id}' с активным планом.")

    # 2. Запуск тестовой логики
    print("\n2. Запуск логики обнаружения...")
    await test_scheduler_logic()

    # 3. Очистка
    await unified_state.clear_user_state(test_user_id)
    print("\n3. Тестовый пользователь удален.")
    print("\n--- Тестирование завершено ---")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main_test())

