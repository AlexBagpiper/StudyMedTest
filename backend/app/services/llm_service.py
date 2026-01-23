"""
LLM Service - абстрактный слой для работы с языковыми моделями
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.system_config import SystemConfig

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """
    Базовый интерфейс для LLM провайдеров
    """
    
    @abstractmethod
    async def evaluate_answer(
        self,
        question: str,
        reference_answer: str,
        student_answer: str,
        criteria: Dict[str, int],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Оценка ответа студента
        
        Returns:
            {
                "criteria_scores": {...},
                "total_score": float,
                "feedback": str
            }
        """
        pass


class YandexGPTProvider(BaseLLMProvider):
    """
    YandexGPT provider
    """
    
    def __init__(self):
        self.default_model = "yandexgpt-lite/latest"
    
    def _get_prompt_variables(self, question: str, reference_answer: str, student_answer: str, criteria: Dict[str, int]) -> Dict[str, Any]:
        """Подготовка переменных для форматирования промпта"""
        vars = {
            "question": question,
            "reference_answer": reference_answer,
            "student_answer": student_answer,
        }
        # Добавляем полные имена критериев
        for k, v in criteria.items():
            vars[f"max_{k}"] = v
        
        # Добавляем сокращенные алиасы для удобства в промптах
        alias_map = {
            "factual_correctness": "factual",
            "completeness": "completeness",
            "terminology": "terminology",
            "structure": "structure"
        }
        for full, short in alias_map.items():
            if full in criteria:
                vars[f"max_{short}"] = criteria[full]
        
        return vars

    async def evaluate_answer(
        self,
        question: str,
        reference_answer: str,
        student_answer: str,
        criteria: Dict[str, int],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Оценка через YandexGPT
        """
        import httpx
        
        config = config or {}
        api_key = config.get("yandex_api_key") or settings.YANDEX_API_KEY
        folder_id = config.get("yandex_folder_id") or settings.YANDEX_FOLDER_ID
        model_name = config.get("yandex_model") or self.default_model
        
        if not api_key or not folder_id:
            return {
                "criteria_scores": {k: 0 for k in criteria.keys()},
                "total_score": 0,
                "feedback": "YandexGPT API key or Folder ID not configured"
            }

        model_uri = f"gpt://{folder_id}/{model_name}"
        
        # Динамический шаблон JSON для критериев
        criteria_template = ",\n    ".join([f'"{k}": <баллы>' for k in criteria.keys()])
        
        custom_prompt = config.get("evaluation_prompt")
        if custom_prompt:
            try:
                prompt_vars = self._get_prompt_variables(question, reference_answer, student_answer, criteria)
                prompt = custom_prompt.format(**prompt_vars)
            except KeyError as e:
                return {
                    "criteria_scores": {k: 0 for k in criteria.keys()},
                    "total_score": 0,
                    "feedback": f"Ошибка в шаблоне промпта: отсутствует переменная {e}"
                }
        else:
            prompt = f"""Ты — эксперт-преподаватель медицины. Оцени ответ студента по критериям.
            
ВОПРОС: {question}
ЭТАЛОН: {reference_answer}
ОТВЕТ СТУДЕНТА: {student_answer}

КРИТЕРИИ:
{self._format_criteria(criteria)}

Верни ответ ТОЛЬКО в формате JSON без пояснений:
{{
  "criteria_scores": {{
    {criteria_template}
  }},
  "total_score": <сумма>,
  "feedback": "<текст>"
}}"""

        try:
            # Определение типа авторизации (API Key или IAM Token)
            auth_header = f"Api-Key {api_key}"
            if api_key.startswith("t1."):
                auth_header = f"Bearer {api_key}"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                    headers={
                        "Authorization": auth_header,
                        "x-folder-id": folder_id
                    },
                    json={
                        "modelUri": model_uri,
                        "completionOptions": {
                            "stream": False,
                            "temperature": 0.1,  # Снижаем температуру для максимальной стабильности
                            "maxTokens": 2000
                        },
                        "messages": [
                            {"role": "system", "text": "Ты эксперт-преподаватель медицины. Отвечай СТРОГО в формате JSON. НЕ используй разметку markdown (```json). Твой ответ должен начинаться с '{' и заканчиваться на '}'."},
                            {"role": "user", "text": prompt}
                        ]
                    },
                    timeout=60.0
                )
                
                if response.status_code != 200:
                    hint = ""
                    if response.status_code == 401:
                        hint = " (Убедитесь, что API Key начинается на 'AQVN'. Указанный вами ключ похож на ID ресурса, а не на секретный ключ)"
                    elif response.status_code == 403:
                        hint = " (Проверьте права доступа сервисного аккаунта и Folder ID 'b1...')"
                    raise Exception(f"YandexGPT error: {response.status_code} {response.text}{hint}")
                
                result_text = response.json()["result"]["alternatives"][0]["message"]["text"]
                
                # Очистка и парсинг JSON
                try:
                    return self._parse_json_response(result_text)
                except Exception as parse_error:
                    logger.error(f"Failed to parse YandexGPT JSON. Raw text: {result_text}")
                    raise parse_error
                
        except Exception as e:
            logger.error(f"YandexGPT evaluation error: {e}")
            return {
                "criteria_scores": {k: 0 for k in criteria.keys()},
                "total_score": 0,
                "feedback": f"Error during YandexGPT evaluation: {str(e)}"
            }

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Устойчивый парсинг JSON из ответа модели"""
        import re
        
        # 1. Предварительная очистка от явных Markdown блоков
        clean_text = text.strip()
        
        # Ищем содержимое между ```json и ``` или просто ``` и ```
        if "```" in clean_text:
            blocks = re.findall(r'```(?:json)?\s*(.*?)\s*```', clean_text, re.DOTALL)
            if blocks:
                clean_text = blocks[0].strip()
        
        # 2. Если JSON все еще не валиден, пытаемся найти границы первой и последней фигурной скобки
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            json_match = re.search(r'(\{.*\})', clean_text, re.DOTALL)
            if json_match:
                clean_text = json_match.group(1)
            
            # 3. Финальные попытки исправления типичных ошибок LLM
            try:
                return json.loads(clean_text)
            except json.JSONDecodeError as e:
                # а) Удаляем лишние запятые перед закрывающими скобками: {"a": 1,} -> {"a": 1}
                clean_text = re.sub(r',\s*([\]\}])', r'\1', clean_text)
                
                # б) Заменяем одинарные кавычки на двойные (очень осторожно)
                # Ищем ключи в одинарных кавычках: 'key': -> "key":
                clean_text = re.sub(r"([\{\[,]\s*)'([^']+)':", r'\1"\2":', clean_text)
                # Ищем строковые значения в одинарных кавычках: : 'value' -> : "value"
                clean_text = re.sub(r":\s*'([^']+)'(\s*[,\]\}])", r': "\1"\2', clean_text)
                
                try:
                    return json.loads(clean_text)
                except:
                    # Если ничего не помогло, выбрасываем ошибку с информативным текстом
                    raise Exception(f"Не удалось распарсить ответ модели как JSON. Ошибка: {str(e)}. Ответ: {text[:150]}...")

    def _format_criteria(self, criteria: Dict[str, int]) -> str:
        return "\n".join([f"- {k.replace('_', ' ').title()}: 0-{v} баллов" 
                         for i, (k, v) in enumerate(criteria.items())])


class LocalLLMProvider(BaseLLMProvider):
    """
    Локальная LLM модель (LLaMA, Mistral через vLLM/Ollama)
    """
    
    def __init__(self):
        pass
    
    async def evaluate_answer(
        self,
        question: str,
        reference_answer: str,
        student_answer: str,
        criteria: Dict[str, int],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Оценка через локальную модель
        """
        import httpx
        
        config = config or {}
        api_url = config.get("local_llm_url") or settings.LOCAL_LLM_URL
        model = config.get("local_llm_model") or settings.LOCAL_LLM_MODEL
        
        if not api_url:
            return {
                "criteria_scores": {k: 0 for k in criteria.keys()},
                "total_score": 0,
                "feedback": "Local LLM URL not configured"
            }

        custom_prompt = config.get("evaluation_prompt")
        if custom_prompt:
            try:
                # Используем тот же хелпер из YandexGPTProvider (или можно вынести его выше)
                # Для простоты пока повторим логику подготовки переменных здесь
                vars = {
                    "question": question,
                    "reference_answer": reference_answer,
                    "student_answer": student_answer,
                }
                for k, v in criteria.items():
                    vars[f"max_{k}"] = v
                
                # Добавляем алиасы
                vars["max_factual"] = criteria.get("factual_correctness", 0)
                vars["max_completeness"] = criteria.get("completeness", 0)
                vars["max_terminology"] = criteria.get("terminology", 0)
                vars["max_structure"] = criteria.get("structure", 0)
                
                prompt = custom_prompt.format(**vars)
            except KeyError as e:
                return {
                    "criteria_scores": {k: 0 for k in criteria.keys()},
                    "total_score": 0,
                    "feedback": f"Ошибка в шаблоне промпта: отсутствует переменная {e}"
                }
        else:
            prompt = f"""Оцени ответ студента. Вопрос: {question}
Эталон: {reference_answer}
Ответ студента: {student_answer}

Верни JSON с оценками по критериям."""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{api_url}/chat/completions", # Используем чат-эндпоинт для единообразия
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "Ты эксперт-преподаватель медицины. Отвечай ТОЛЬКО в формате JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 1000,
                        "temperature": 0.3,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=60.0
                )
                
                result = response.json()["choices"][0]["message"]["content"]
                
                # Попытка парсинга JSON из ответа
                try:
                    if isinstance(result, str):
                        return json.loads(result)
                    return result
                except:
                    # Fallback - простая оценка
                    return {
                        "criteria_scores": {k: v // 2 for k, v in criteria.items()},
                        "total_score": sum(criteria.values()) // 2,
                        "feedback": "Оценка выполнена локальной моделью (ошибка парсинга JSON)"
                    }
        
        except Exception as e:
            logger.error(f"Local LLM evaluation error: {e}")
            return {
                "criteria_scores": {k: 0 for k in criteria.keys()},
                "total_score": 0,
                "feedback": f"Error: {str(e)}"
            }


class LLMRouter:
    """
    Роутер для выбора LLM провайдера
    """
    
    def __init__(self):
        self.providers = {
            "local": LocalLLMProvider(),
            "yandex": YandexGPTProvider()
        }
    
    def get_provider(self, strategy: str, priority: str = "normal") -> BaseLLMProvider:
        """
        Выбор провайдера по стратегии
        
        Args:
            strategy: local | hybrid | yandex
            priority: "critical" для важных задач, "normal" для обычных
        """
        if strategy == "yandex":
            return self.providers["yandex"]
        
        elif strategy == "local":
            return self.providers["local"]
        
        elif strategy == "hybrid":
            # Пока гибрид использует яндекс для критичных
            if priority == "critical":
                return self.providers["yandex"]
            return self.providers["local"]
        
        # Fallback
        default_strategy = settings.LLM_STRATEGY
        if default_strategy == "local":
            return self.providers["local"]
        return self.providers["yandex"]


class LLMService:
    """
    Главный сервис для работы с LLM
    """
    
    def __init__(self):
        self.router = LLMRouter()

    async def _get_db_config(self, db: AsyncSession) -> Dict[str, Any]:
        """Получение настроек из БД"""
        try:
            result = await db.execute(
                select(SystemConfig).where(SystemConfig.key == "llm_evaluation_params")
            )
            config_obj = result.scalar_one_or_none()
            return config_obj.value if config_obj else {}
        except Exception as e:
            logger.error(f"Error fetching LLM config from DB: {e}")
            return {}
    
    async def evaluate_text_answer(
        self,
        question: str,
        reference_answer: str,
        student_answer: str,
        criteria: Optional[Dict[str, int]] = None,
        priority: str = "normal",
        db: Optional[AsyncSession] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Оценка текстового ответа с поддержкой fallback
        """
        if criteria is None:
            criteria = {
                "factual_correctness": 40,
                "completeness": 30,
                "terminology": 20,
                "structure": 10,
            }
        
        # Приоритет: переданный конфиг -> конфиг из БД -> settings из .env
        db_config = config
        if db_config is None and db:
            db_config = await self._get_db_config(db)
        
        db_config = db_config or {}
        
        strategy = db_config.get("strategy") or settings.LLM_STRATEGY
        fallback_enabled = db_config.get("fallback_enabled", True)
        
        # 1. Первая попытка
        provider = self.router.get_provider(strategy, priority)
        try:
            result = await provider.evaluate_answer(
                question=question,
                reference_answer=reference_answer,
                student_answer=student_answer,
                criteria=criteria,
                config=db_config
            )
            
            # Проверяем, не вернул ли провайдер ошибку внутри результата
            if result.get("total_score") == 0 and "Error" in result.get("feedback", ""):
                raise Exception(result["feedback"])
                
            result["provider"] = provider.__class__.__name__
            return result

        except Exception as e:
            logger.warning(f"Primary LLM provider ({provider.__class__.__name__}) failed: {e}")
            
            if not fallback_enabled:
                raise

            # 2. Попытка через запасной вариант
            fallback_strategy = "local" if strategy != "local" else "yandex"
            fallback_provider = self.router.get_provider(fallback_strategy, priority)
            
            logger.info(f"Attempting fallback to {fallback_provider.__class__.__name__}")
            
            try:
                result = await fallback_provider.evaluate_answer(
                    question=question,
                    reference_answer=reference_answer,
                    student_answer=student_answer,
                    criteria=criteria,
                    config=db_config
                )
                result["provider"] = f"{fallback_provider.__class__.__name__} (Fallback)"
                return result
            except Exception as fallback_e:
                logger.error(f"Fallback LLM provider also failed: {fallback_e}")
                return {
                    "criteria_scores": {k: 0 for k in criteria.keys()},
                    "total_score": 0,
                    "feedback": f"Все модели оценки недоступны. Ошибка: {str(e)}",
                    "provider": "None"
                }


# Singleton
llm_service = LLMService()

