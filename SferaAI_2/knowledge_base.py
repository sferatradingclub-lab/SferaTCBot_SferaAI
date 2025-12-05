import os
import sys
from dotenv import load_dotenv
from qdrant_client import AsyncQdrantClient, models
from fastembed import TextEmbedding, SparseTextEmbedding

# --- Конфигурация ---
load_dotenv()

COLLECTION_NAME = "global_knowledge_base"
DENSE_VECTOR_NAME = "dense_kb"
SPARSE_VECTOR_NAME = "sparse_kb"
DENSE_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SPARSE_MODEL_NAME = "prithivida/Splade_PP_en_v1"

# --- Async Клиент Qdrant ---
client = AsyncQdrantClient(
    url=os.getenv("QDRANT_HOST"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

# --- Модели Эмбедингов (глобальная инициализация для эффективности) ---
try:
    dense_model = TextEmbedding(model_name=DENSE_MODEL_NAME)
    sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL_NAME)
except Exception as e:
    print(f"Критическая ошибка: не удалось загрузить модели эмбедингов: {e}", file=sys.stderr)
    sys.exit(1)


def recreate_collection():
    """
    Пересоздает коллекцию 'global_knowledge_base' с правильной конфигурацией:
    - Именованные векторы (dense и sparse)
    - Payload-индексы для всех полей фильтрации
    """
    try:
        # Проверяем, существует ли коллекция, и удаляем ее, если да
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        if COLLECTION_NAME in collection_names:
            print(f"Коллекция '{COLLECTION_NAME}' уже существует. Удаляю ее...")
            client.delete_collection(collection_name=COLLECTION_NAME)
            print("Коллекция удалена.")

        # Создаем коллекцию с именованными векторами
        print(f"Создание коллекции '{COLLECTION_NAME}'...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                DENSE_VECTOR_NAME: models.VectorParams(
                    size=len(list(dense_model.embed(["test"]))[0]),
                    distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={
                SPARSE_VECTOR_NAME: models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=False)
                )
            }
        )
        print("Коллекция успешно создана.")

        # Создаем payload-индексы для полей, по которым будет идти фильтрация
        print("Создание payload-индексов...")
        fields_to_index = [
            ("doc_type", "keyword"),
            ("doc_id", "keyword"),
            ("content_type", "keyword"),
            ("category_1", "keyword"),
            ("category_2", "keyword"),
            ("difficulty_level", "keyword"),
        ]
        for field, field_type in fields_to_index:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field,
                field_schema=field_type
            )
            print(f" - Индекс для поля '{field}' создан.")
        
        print("Все payload-индексы успешно созданы.")

    except Exception as e:
        print(f"Произошла ошибка при пересоздании коллекции: {e}", file=sys.stderr)
        sys.exit(1)


async def query_knowledge_base(user_query: str, persona: str = "partner", filters: dict = None) -> str:
    """
    Выполняет двухэтапный запрос к КВ с динамической фильтрацией:
    1. Гибридный поиск 'summary' с учетом персоны и фильтров.
    2. Упорядоченное извлечение всех 'content' шагов этого документа.
    Возвращает отформатированный контекст для LLM.
    """
    print(f"\n--- ЭТАП 1: Обнаружение (Гибридный Поиск) ---")
    print(f"Запрос: \"{user_query}\", Персона: {persona}, Фильтры: {filters}")

    try:
        # Шаг 1: Построение динамического фильтра
        filter_conditions = [
            models.FieldCondition(key="doc_type", match=models.MatchValue(value="summary"))
        ]
        if persona == "psychologist":
            filter_conditions.append(models.FieldCondition(key="content_type", match=models.MatchValue(value="psychology")))
        elif persona == "mentor":
            filter_conditions.append(models.FieldCondition(key="content_type", match=models.MatchValue(value="trading")))
        
        if filters:
            for key, value in filters.items():
                filter_conditions.append(models.FieldCondition(key=key, match=models.MatchValue(value=value)))
        
        dynamic_filter = models.Filter(must=filter_conditions)
        print(f"Собранный фильтр для Qdrant: {dynamic_filter.json()}")

        # Шаг 2: Вручную генерируем векторы для запроса
        dense_query_vector = list(dense_model.embed([user_query]))[0].tolist()
        sparse_query_vector_raw = list(sparse_model.embed([user_query]))[0]
        sparse_query_vector = models.SparseVector(
            indices=sparse_query_vector_raw.indices.tolist(),
            values=sparse_query_vector_raw.values.tolist()
        )

        # Этап 3: Обнаружение (Discovery) с использованием векторов и динамического фильтра
        discovery_results = await client.query_points(
            collection_name=COLLECTION_NAME,
            query=models.FusionQuery(
                fusion=models.Fusion.RRF,
            ),
            prefetch=[
                models.Prefetch(
                    query=dense_query_vector,
                    using=DENSE_VECTOR_NAME,
                    limit=5
                ),
                models.Prefetch(
                    query=sparse_query_vector,
                    using=SPARSE_VECTOR_NAME,
                    limit=5
                )
            ],
            query_filter=dynamic_filter, # Используем динамический фильтр
            limit=1,
            with_payload=True
        )
    except Exception as e:
        print(f"Ошибка гибридного поиска: {e}")
        return "Ошибка: не удалось выполнить гибридный поиск."

    if not discovery_results.points:
        print("--- Результат: Ничего не найдено ---")
        return "К сожалению, я не нашел информации по вашему запросу в базе знаний."

    best_summary_point = discovery_results.points[0]
    doc_id_to_fetch = best_summary_point.payload["doc_id"]
    doc_title = best_summary_point.payload["title"]

    print(f"Найден документ: \"{doc_title}\" (ID: {doc_id_to_fetch})")

    # Этап 2: Извлечение (Retrieval)
    print(f"\n--- ЭТАП 2: Извлечение (Упорядоченный Scroll) ---")
    try:
        retrieval_results = await client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="doc_id",
                        match=models.MatchValue(value=doc_id_to_fetch)
                    ),
                    models.FieldCondition(
                        key="doc_type",
                        match=models.MatchValue(value="content")
                    )
                ]
            ),
            limit=100,
            with_payload=True,
            order_by=models.OrderBy(
                key="step_number",
                direction=models.Direction.ASC
            )
        )
    except Exception as e:
        print(f"Ошибка при извлечении шагов (scroll): {e}")
        return f"Ошибка: не удалось извлечь шаги для документа '{doc_title}'."

    if not retrieval_results[0]:
        print("--- Результат: Найден summary, но не найдены шаги ---")
        return f"Я нашел курс '{doc_title}', но не смог загрузить его шаги."

    # Этап 3: Формирование ответа для LLM
    print(f"Сборка ответа из {len(retrieval_results[0])} шагов...")
    
    final_context = (
        f"Инструкция для Агента: Ты должен составить ответ на основе следующего курса:\n"
        f"Название курса: \"{doc_title}\"\n"
        f"Обзор курса: {best_summary_point.payload['source_text']}\n\n"
        f"Пошаговый План:\n"
    )

    for point in retrieval_results[0]:
        payload = point.payload
        final_context += (
            f"--- Шаг {payload['step_number']}: {payload['step_title']} ---\n"
            f"{payload['source_text']}\n\n"
        )

    return final_context

if __name__ == '__main__':
    # --- Пересоздание и настройка коллекции ---
    # Этот блок кода вызывается при прямом запуске скрипта.
    # Он полностью удаляет и заново создает коллекцию 'global_knowledge_base'
    # с правильной схемой векторов и всеми необходимыми payload-индексами.
    # Это необходимо выполнить один раз перед первым запуском ETL-пайплайна.
    # print("--- ЗАПУСК НАСТРОЙКИ КОЛЛЕКЦИИ QDRANT ---")
    # recreate_collection()
    # print("\n--- НАСТРОЙКА КОЛЛЕКЦИИ УСПЕШНО ЗАВЕРШЕНА ---")
    
    # --- Пример Запроса (можно раскомментировать для проверки) ---
    print("\n--- ПРОВЕРКА: Пример запроса к базе знаний ---")
    query = "Как мне бороться с тильтом?"
    # persona="psychologist" # "partner", "mentor", "psychologist"
    # filters = {"category_2": "revenge_trading"}
    context_for_llm = query_knowledge_base(query, persona="psychologist", filters={})
    print("\n--- ИТОГОВЫЙ КОНТЕКСТ ДЛЯ LLM ---")
    print(context_for_llm)
