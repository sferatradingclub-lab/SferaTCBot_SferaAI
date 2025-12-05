import sys
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

# --- Конфигурация ---
# Загрузка переменных окружения из .env файла
load_dotenv()

# Модели, которые мы будем использовать для генерации векторов
DENSE_MODEL_NAME = "BAAI/bge-small-en-v1.5"
# Имена наших именованных векторов
DENSE_VECTOR_NAME = "dense_kb"
SPARSE_VECTOR_NAME = "sparse_kb"
# Имя коллекции
COLLECTION_NAME = "global_knowledge_base"

# --- Клиент Qdrant ---
# Используем учетные данные из .env файла
client = QdrantClient(
    url=os.getenv("QDRANT_HOST"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

def setup_knowledge_base():
    """
    Создает и настраивает коллекцию для глобальной базы знаний.
    - Удаляет существующую коллекцию, если она есть.
    - Создает новую коллекцию с конфигурацией для dense и sparse векторов.
    - Создает индексы payload для быстрой фильтрации и сортировки.
    """
    # --- Шаг 1: Определение Схемы Коллекции ---
    print("--- Шаг 1: Определение Схемы Коллекции ---")
    try:
        # Qdrant-client с fastembed может сам получить размерность
        dense_vector_size = client.get_embedding_size(DENSE_MODEL_NAME)
        print(f"Размерность DENSE вектора ({DENSE_MODEL_NAME}): {dense_vector_size}")
    except Exception as e:
        print(f"Не удалось автоматически получить размерность {DENSE_MODEL_NAME}. Используем 384. Ошибка: {e}")
        dense_vector_size = 384

    # Конфигурация для DENSE векторов (семантика)
    vectors_config = {
        DENSE_VECTOR_NAME: models.VectorParams(
            size=dense_vector_size,
            distance=models.Distance.COSINE  # Стандарт для dense-эмбедингов
        )
    }

    # Конфигурация для SPARSE векторов (ключевые слова)
    sparse_vectors_config = {
        SPARSE_VECTOR_NAME: models.SparseVectorParams(
            # Для sparse-моделей (BM25/SPLADE) рекомендуется
            # включить модификатор IDF
            modifier=models.Modifier.IDF
        )
    }

    # --- Шаг 2: Создание коллекции ---
    print("\n--- Шаг 2: Создание коллекции ---")
    try:
        if client.collection_exists(collection_name=COLLECTION_NAME):
            print(f"Коллекция {COLLECTION_NAME} уже существует. Пересоздание...")
            client.delete_collection(collection_name=COLLECTION_NAME)

        print(f"Создание новой коллекции {COLLECTION_NAME}...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=vectors_config,
            sparse_vectors_config=sparse_vectors_config
        )
        print(f"Коллекция {COLLECTION_NAME} успешно создана.")

        # Проверка конфигурации
        collection_info = client.get_collection(collection_name=COLLECTION_NAME)
        print("\n--- Конфигурация Коллекции ---")
        print(collection_info.config)
        print("---------------------------------")

    except Exception as e:
        print(f"Произошла ошибка при создании коллекции: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Шаг 3: Индексация payload ---
    print("\n--- Шаг 3: Создание индексов payload ---")
    try:
        # Индекс для 'topic' (keyword)
        print("Создание индекса для 'topic' (keyword)...")
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="topic",
            field_schema=models.PayloadSchemaType.KEYWORD,
            wait=True
        )

        # Индекс для 'doc_type' (keyword)
        print("Создание индекса для 'doc_type' (keyword)...")
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="doc_type",
            field_schema=models.PayloadSchemaType.KEYWORD,
            wait=True
        )

        # Индекс для 'doc_id' (keyword)
        print("Создание индекса для 'doc_id' (keyword)...")
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="doc_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
            wait=True
        )

        # Индекс для 'step_number' (integer) с поддержкой range
        print("Создание индекса для 'step_number' (integer)...")
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="step_number",
            field_schema=models.IntegerIndexParams(
                type=models.IntegerIndexType.INTEGER,
                lookup=True,
                range=True  # Обязательно для order_by
            ),
            wait=True
        )
        print("Индексы payload успешно созданы.")

        # Проверка созданных индексов
        collection_info = client.get_collection(collection_name=COLLECTION_NAME)
        print("\n--- Схема Индексов Payload ---")
        print(collection_info.payload_schema)
        print("-----------------------------")

    except Exception as e:
        print(f"Произошла ошибка при создании индексов: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    setup_knowledge_base()
