import google.generativeai as genai
import json
from google.oauth2 import service_account
import os

print("--- Начинаем диагностику доступных моделей Gemini ---")

try:
    # Используем тот же надежный способ найти файл, что и в прошлый раз
    project_root = os.path.dirname(os.path.abspath(__file__))
    credentials_path = os.path.join(project_root, 'credentials.json')

    print(f"1. Загружаем ключ из '{credentials_path}'...")
    with open(credentials_path) as f:
        credentials_info = json.load(f)
    credentials = service_account.Credentials.from_service_account_info(credentials_info)
    print("   ...Ключ успешно загружен.")

    # Конфигурируем клиент
    genai.configure(credentials=credentials)

    print("\n2. Запрашиваем у Google список доступных моделей...")
    
    # Получаем и выводим список моделей
    print("-" * 30)
    print("СПИСОК ДОСТУПНЫХ МОДЕЛЕЙ:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
    print("-" * 30)
    
    print("\n✅ Диагностика завершена. Пожалуйста, отправьте этот список вашему ассистенту.")

except FileNotFoundError:
    print(f"\n❌ ОШИБКА: Файл '{credentials_path}' не найден. Убедитесь, что он лежит в корневой папке проекта.")
except Exception as e:
    print(f"\n❌ ПРОИЗОШЛА ОШИБКА:")
    print(e)