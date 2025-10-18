#!/usr/bin/env python3
"""
Локальный скрипт для тестирования CI/CD pipeline.
Запускает тесты, линтеры и проверку покрытия аналогично GitHub Actions.
"""

import subprocess
import sys
from pathlib import Path


def run_command(command: str, description: str) -> bool:
    """Выполнить команду и вернуть результат."""
    print(f"\n🚀 {description}")
    print(f"Команда: {command}")
    print("-" * 50)
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            print("📤 Вывод:")
            print(result.stdout)
        
        if result.stderr:
            print("⚠️  Предупреждения/Ошибки:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} - УСПЕХ")
            return True
        else:
            print(f"❌ {description} - ПРОВАЛ (код: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ {description} - ОШИБКА: {e}")
        return False


def main():
    """Основная функция для запуска локального CI."""
    print("🔧 Локальное тестирование CI/CD pipeline")
    print("=" * 60)
    
    # Проверяем что мы в правильной директории
    if not Path("requirements.txt").exists():
        print("❌ Ошибка: Запустите скрипт из корневой директории проекта")
        sys.exit(1)
    
    # Устанавливаем зависимости для тестирования
    if not run_command(
        "pip install pytest-cov flake8 black mypy",
        "Установка зависимостей для тестирования"
    ):
        sys.exit(1)
    
    success_count = 0
    total_count = 0
    
    # 1. Линтинг с flake8
    total_count += 1
    if run_command(
        "flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics",
        "Линтинг с flake8 (критические ошибки)"
    ):
        success_count += 1
    
    # 2. Линтинг с flake8 (все предупреждения)
    total_count += 1
    if run_command(
        "flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics",
        "Линтинг с flake8 (все предупреждения)"
    ):
        success_count += 1
    
    # 3. Проверка форматирования с black
    total_count += 1
    if run_command(
        "black --check --diff .",
        "Проверка форматирования с black"
    ):
        success_count += 1
    
    # 4. Проверка типов с mypy
    total_count += 1
    if run_command(
        "mypy . --ignore-missing-imports",
        "Проверка типов с mypy"
    ):
        success_count += 1
    
    # 5. Запуск тестов с покрытием
    total_count += 1
    if run_command(
        "pytest --cov=. --cov-report=term-missing --cov-report=html:htmlcov --cov-fail-under=80",
        "Запуск тестов с проверкой покрытия"
    ):
        success_count += 1
    
    # 6. Генерация отчета о покрытии
    total_count += 1
    if run_command(
        "pytest --cov=. --cov-report=xml",
        "Генерация XML отчета о покрытии"
    ):
        success_count += 1
    
    # Результаты
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ЛОКАЛЬНОГО CI")
    print(f"Успешно: {success_count}/{total_count}")
    print(f"Процент успеха: {round((success_count/total_count)*100, 1)}%")
    
    if success_count == total_count:
        print("🎉 Все проверки пройдены! Готово к коммиту.")
        return 0
    else:
        print("⚠️  Некоторые проверки провалились. Исправьте ошибки перед коммитом.")
        return 1


if __name__ == "__main__":
    sys.exit(main())