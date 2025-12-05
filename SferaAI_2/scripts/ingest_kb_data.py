import uuid
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding, SparseTextEmbedding
import sys

# --- Конфигурация ---
# Загрузка переменных окружения из .env файла
load_dotenv()

# Модели, которые мы будем использовать для генерации векторов
DENSE_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SPARSE_MODEL_NAME = "prithivida/Splade_PP_en_v1"
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

def ingest_data():
    """
    Преобразует сырой контент в точки PointStruct и загружает их в Qdrant.
    """
    # --- Шаг 1: Инициализация моделей эмбедингов ---
    print("--- Шаг 1: Загрузка моделей FastEmbed ---")
    try:
        dense_model = TextEmbedding(model_name=DENSE_MODEL_NAME)
        sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL_NAME)
        print("Модели успешно загружены.")
    except Exception as e:
        print(f"Ошибка при загрузке моделей: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Шаг 2: Определение сырых данных (наш курс) ---
    print("\n--- Шаг 2: Определение сырых данных ---")
    course_doc_id = "trading_psych_101"  # Общий ID для всех частей курса
    documents_to_ingest = [
        {
            "doc_type": "summary",
            "topic": "trading_psychology",
            "title": "Полный курс: Психология трейдинга и управление эмоциями",
            "source_text": "Этот курс научит вас управлять FOMO, избегать тильта и разрабатывать дисциплинированный подход к торговле. Он охватывает ключевые психологические ловушки и методы их преодоления."
        },
        {
            "doc_type": "content",
            "topic": "trading_psychology",
            "step_number": 1,
            "step_title": "Шаг 1: Признание и идентификация FOMO",
            "source_text": "FOMO (Fear of Missing Out) - это первая проблема, с которой сталкиваются трейдеры. Это эмоциональное состояние, когда вы боитесь упустить прибыльную сделку, что часто приводит к импульсивным и убыточным решениям."
        },
        {
            "doc_type": "content",
            "topic": "trading_psychology",
            "step_number": 2,
            "step_title": "Шаг 2: Техники выхода из тильта",
            "source_text": "Тильт - это состояние гнева или фрустрации после серии убытков, которое заставляет трейдера отходить от своего торгового плана и принимать иррациональные решения."
        },
        {
            "doc_type": "content",
            "topic": "trading_psychology",
            "step_number": 3,
            "step_title": "Шаг 3: Разработка торгового плана",
            "source_text": "Торговый план - ваш главный инструмент против эмоций. Он должен четко определять ваши точки входа, выхода, размер позиции и стратегию управления рисками, включая stop-loss."
        }
    ]
    print(f"Подготовлено {len(documents_to_ingest)} документов для загрузки.")

    # --- Шаг 3: Генерация векторов и PointStruct ---
    print("\n--- Шаг 3: Генерация векторов и PointStruct ---")
    
    # Разделяем тексты для пакетной генерации эмбедингов
    texts = [doc["source_text"] for doc in documents_to_ingest]
    
    print(f"Генерация {len(texts)} dense-векторов...")
    dense_embeddings = list(dense_model.embed(texts))
    
    print(f"Генерация {len(texts)} sparse-векторов...")
    sparse_embeddings = list(sparse_model.embed(texts))
    
    print("Формирование объектов PointStruct...")
    points_to_upload = []
    for i, doc in enumerate(documents_to_ingest):
        # Генерация sparse-вектора в формате Qdrant
        sparse_qdrant_vector = models.SparseVector(
            indices=sparse_embeddings[i].indices.tolist(),
            values=sparse_embeddings[i].values.tolist()
        )
        
        # Собираем payload в соответствии с нашей схемой
        payload = {
            "doc_id": course_doc_id,
            "doc_type": doc["doc_type"],
            "topic": doc.get("topic", "general"), # .get для безопасности
            "source_text": doc["source_text"] # Всегда храним сырой текст
        }
        
        # Добавляем специфичные поля
        if doc["doc_type"] == "summary":
            payload["title"] = doc["title"]
        else:
            payload["step_number"] = doc["step_number"]
            payload["step_title"] = doc["step_title"]
            
        # Формируем PointStruct с ИМЕНОВАННЫМИ векторами
        point = models.PointStruct(
            id=str(uuid.uuid4()),  # Уникальный ID для каждой точки
            payload=payload,
            vector={
                DENSE_VECTOR_NAME: dense_embeddings[i].tolist(),
                SPARSE_VECTOR_NAME: sparse_qdrant_vector
            }
        )
        points_to_upload.append(point)
    
    print(f"Сформировано {len(points_to_upload)} точек.")

    # --- Шаг 4: Пакетная Загрузка ---
    print("\n--- Шаг 4: Пакетная загрузка данных ---")
    try:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points_to_upload,
            wait=True  # Ожидать завершения операции
        )
        print("Загрузка успешно завершена.")
        
        # Проверка количества точек в коллекции
        count_result = client.count(collection_name=COLLECTION_NAME, exact=True)
        print(f"Количество точек в коллекции '{COLLECTION_NAME}': {count_result.count}")

    except Exception as e:
        print(f"Произошла ошибка при загрузке данных: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    ingest_data()
