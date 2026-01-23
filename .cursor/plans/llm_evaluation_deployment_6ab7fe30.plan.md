---
name: LLM Evaluation Deployment
overview: Пошаговый план развертывания системы автоматической проверки текстовых ответов студентов с использованием LLM, включая выбор моделей, инфраструктуру и настройку качества.
todos:
  - id: env-setup
    content: Настроить переменные окружения (API ключи, стратегия LLM)
    status: pending
  - id: local-llm
    content: (Опционально) Развернуть локальную модель через vLLM или Ollama
    status: pending
  - id: celery-worker
    content: Настроить и запустить Celery worker для LLM-очереди
    status: pending
  - id: prompt-tuning
    content: Улучшить промпт для медицинской оценки
    status: pending
  - id: monitoring
    content: Добавить логирование и метрики для LLM-запросов
    status: pending
  - id: caching
    content: Реализовать кэширование результатов оценки в Redis
    status: pending
  - id: benchmark
    content: Создать benchmark-набор и провести калибровку качества
    status: pending
  - id: admin-ui
    content: Добавить UI настроек LLM в админку (аналогично CVSettings)
    status: pending
---

# План развертывания LLM-оценки текстовых ответов

## 1. Текущее состояние

Базовая архитектура уже реализована в проекте:

- **LLM Service**: [backend/app/services/llm_service.py](backend/app/services/llm_service.py) - абстрактный слой с провайдерами
- **Celery Tasks**: [backend/app/tasks/evaluation_tasks.py](backend/app/tasks/evaluation_tasks.py) - асинхронная обработка
- **Config**: [backend/app/core/config.py](backend/app/core/config.py) - переменные окружения

---

## 2. Выбор LLM-модели

### 2.1 Сравнение вариантов

| Параметр | GPT-4o | GPT-4o-mini | Claude 3.5 Sonnet | Llama 3.1 70B (local) | Mistral 7B (local) |

|----------|--------|-------------|-------------------|----------------------|-------------------|

| Качество оценки | Отличное | Хорошее | Отличное | Хорошее | Удовл. |

| Стоимость/1M токенов | ~$5 input/$15 out | ~$0.15/$0.60 | ~$3/$15 | Бесплатно | Бесплатно |

| Латентность | 2-5 сек | 1-3 сек | 2-4 сек | 5-15 сек | 2-5 сек |

| Требования к GPU | - | - | - | A100 80GB / 2xA6000 | RTX 3090 / A4000 |

| Контекст (токены) | 128K | 128K | 200K | 128K | 32K |

| JSON-режим | Да | Да | Да | Частично | Частично |

### 2.2 Рекомендуемая стратегия: Hybrid

```
КРИТИЧНЫЕ ЭКЗАМЕНЫ → GPT-4o (максимальное качество)
ТЕКУЩИЕ ТЕСТЫ     → GPT-4o-mini (баланс цена/качество)
МАССОВАЯ ПРОВЕРКА → Local Llama/Mistral (нулевая стоимость)
```

---

## 3. Инфраструктурные требования

### 3.1 Для облачных моделей (OpenAI/Anthropic)

- Стабильный интернет
- API ключ (~$50-200/мес при 2000 студентов)
- Redis для кэширования (уже есть)

### 3.2 Для локальных моделей

**Минимальные требования (Mistral 7B):**

- GPU: NVIDIA RTX 3090 (24GB VRAM) или A4000
- RAM: 32GB
- SSD: 50GB

**Рекомендуемые (Llama 3.1 70B):**

- GPU: NVIDIA A100 80GB или 2x A6000 48GB
- RAM: 128GB
- SSD: 200GB
- vLLM для inference (tensor parallelism)

---

## 4. Пошаговое развертывание

### Шаг 1: Настройка переменных окружения

Файл `.env`:

```env
# Облачные провайдеры
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

# Локальная модель (если используется)
LOCAL_LLM_ENABLED=true
LOCAL_LLM_URL=http://localhost:8001/v1
LOCAL_LLM_MODEL=meta-llama/Llama-3.1-70B-Instruct

# Стратегия: cloud | local | hybrid
LLM_STRATEGY=hybrid
LLM_FALLBACK_ENABLED=true
```

### Шаг 2: Развертывание локальной модели (опционально)

**Вариант A: vLLM (production)**

```bash
# Docker с GPU
docker run --gpus all -p 8001:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-3.1-70B-Instruct \
  --tensor-parallel-size 2
```

**Вариант B: Ollama (dev/staging)**

```bash
# Установка
curl -fsSL https://ollama.com/install.sh | sh

# Запуск модели
ollama run mistral:7b-instruct-v0.3
```

### Шаг 3: Запуск Celery worker для LLM

```bash
# Отдельный worker для LLM-задач
celery -A app.tasks.celery_app worker \
  --queues=llm \
  --concurrency=4 \
  --loglevel=info
```

### Шаг 4: Тестирование оценки

```python
# backend/tests/test_llm_evaluation.py
import asyncio
from app.services.llm_service import llm_service

async def test():
    result = await llm_service.evaluate_text_answer(
        question="Опишите строение клетки",
        reference_answer="Клетка состоит из мембраны, цитоплазмы и ядра...",
        student_answer="Клетка имеет оболочку и внутреннее содержимое",
        priority="normal"
    )
    print(result)

asyncio.run(test())
```

---

## 5. Настройка промптов

### 5.1 Текущий промпт (базовый)

Находится в `llm_service.py`, метод `OpenAIProvider.evaluate_answer()`.

### 5.2 Улучшенный промпт (рекомендация)

```python
EVALUATION_PROMPT = """
Ты — эксперт-преподаватель медицины с 20-летним опытом. 
Оцени ответ студента объективно и строго.

## КОНТЕКСТ
- Дисциплина: Медицина
- Уровень: Студент медицинского вуза

## ВОПРОС
{question}

## ЭТАЛОННЫЙ ОТВЕТ
{reference_answer}

## ОТВЕТ СТУДЕНТА
{student_answer}

## КРИТЕРИИ ОЦЕНКИ
1. Фактическая правильность (0-{max_factual}):
   - Отсутствие медицинских ошибок
   - Соответствие современным данным
   
2. Полнота ответа (0-{max_completeness}):
   - Раскрытие всех аспектов вопроса
   - Наличие ключевых понятий из эталона
   
3. Терминология (0-{max_terminology}):
   - Использование профессиональных терминов
   - Правильность их применения
   
4. Структура (0-{max_structure}):
   - Логичность изложения
   - Связность текста

## ИНСТРУКЦИИ
- Сравни ответ студента с эталоном
- Учитывай синонимы и перефразирования
- Не снижай баллы за стиль изложения
- Будь объективен: хороший ответ = высокий балл

## ФОРМАТ ОТВЕТА (строго JSON)
{{
  "criteria_scores": {{
    "factual_correctness": <число>,
    "completeness": <число>,
    "terminology": <число>,
    "structure": <число>
  }},
  "total_score": <сумма>,
  "feedback": "<2-3 предложения: что хорошо, что улучшить>"
}}
"""
```

---

## 6. Мониторинг и качество

### 6.1 Метрики для отслеживания

- **Латентность**: время ответа LLM (target: < 10 сек)
- **Стоимость**: расход токенов/денег в день
- **Ошибки**: % failed evaluations
- **Согласованность**: корреляция оценок LLM с ручной проверкой

### 6.2 Логирование

Добавить в `llm_service.py`:

```python
import logging
logger = logging.getLogger("llm")

# В методе evaluate_answer:
logger.info(f"LLM evaluation: provider={provider}, tokens={usage}, latency={elapsed}ms")
```

### 6.3 Кэширование (уже есть Redis)

Добавить кэш для идентичных вопросов:

```python
import hashlib
cache_key = hashlib.md5(f"{question}:{student_answer}".encode()).hexdigest()
```

---

## 7. Калибровка качества

### 7.1 Создание benchmark-набора

1. Собрать 50-100 реальных ответов студентов
2. Получить экспертные оценки от преподавателей
3. Прогнать через LLM
4. Сравнить корреляцию (target: Pearson r > 0.85)

### 7.2 A/B тестирование моделей

Параллельно оценивать одни ответы разными моделями, сравнивать:

- GPT-4o vs GPT-4o-mini
- OpenAI vs Local Llama
- Разные версии промптов

---

## 8. Оценка стоимости (2000 студентов)

### Сценарий: 10 тестов/семестр, 20 вопросов/тест

| Модель | Токенов/ответ | Стоимость/ответ | Всего/семестр |

|--------|---------------|-----------------|---------------|

| GPT-4o | ~2000 | ~$0.04 | ~$16,000 |

| GPT-4o-mini | ~2000 | ~$0.003 | ~$1,200 |

| Claude 3.5 | ~2000 | ~$0.03 | ~$12,000 |

| Local Llama | ~2000 | $0 | $0 + электричество |

**Рекомендация**: GPT-4o-mini для баланса качества и стоимости, или hybrid с локальной моделью.

---

## 9. Чеклист развертывания

- [ ] Получить API ключ OpenAI/Anthropic
- [ ] Настроить `.env` с ключами и стратегией
- [ ] (Опционально) Развернуть локальную модель через vLLM/Ollama
- [ ] Запустить Celery worker с очередью `llm`
- [ ] Протестировать оценку на тестовых данных
- [ ] Настроить мониторинг (логи, метрики)
- [ ] Провести калибровку на benchmark-наборе
- [ ] Документировать настройки для production