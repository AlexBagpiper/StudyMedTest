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
        
        # Добавляем критерии текстом
        vars["criteria_text"] = self._format_criteria(criteria)
        
        return vars

    def _format_criteria(self, criteria: Dict[str, int]) -> str:
        return "\n".join([f"- {k.replace('_', ' ').title()}: 0-{v} баллов" 
                         for i, (k, v) in enumerate(criteria.items())])

    def _prepare_full_prompt(self, question: str, reference_answer: str, student_answer: str, criteria: Dict[str, int], config: Dict[str, Any]) -> str:
        """Сборка полного промпта с учетом анти-чита"""
        
        # 1. Базовый системный промпт (из БД или дефолтный)
        custom_prompt = config.get("evaluation_prompt")
        
        # Динамический шаблон JSON для критериев
        criteria_template = ",\n    ".join([f'"{k}": <баллы>' for k in criteria.keys()])
        
        if not custom_prompt:
            custom_prompt = f"""Ты — эксперт-преподаватель медицины. Оцени ответ студента по критериям.
            
ВОПРОС: {{question}}
ЭТАЛОН: {{reference_answer}}
ОТВЕТ СТУДЕНТА: {{student_answer}}

КРИТЕРИИ:
{{criteria_text}}

Верни ответ ТОЛЬКО в формате JSON:
{{
  "criteria_scores": {{
    {criteria_template}
  }},
  "total_score": <сумма>,
  "feedback": "<текст>"
}}"""

        # 2. Доп. промпты анти-чита
        extra_prompts = ""
        json_extras = ""
        
        # Детекция ИИ
        if config.get("ai_check_enabled") and config.get("ai_check_prompt"):
            extra_prompts += config.get("ai_check_prompt")
            json_extras += ',\n  "ai_probability": <вероятность ИИ от 0.0 до 1.0>'
            
        # Анализ поведения
        if config.get("event_log") and config.get("integrity_check_prompt"):
            extra_prompts += config.get("integrity_check_prompt")
            json_extras += ',\n  "integrity_score": <коэффициент честности от 0.0 до 1.0>,\n  "integrity_feedback": "<краткий комментарий по поведению>"'

        # 3. Форматирование базового промпта
        prompt_vars = self._get_prompt_variables(question, reference_answer, student_answer, criteria)
        
        # Вставляем event_log если он есть
        if config.get("event_log"):
            # Форматируем лог событий для читаемости человеком/моделью
            events = config.get("event_log")
            event_log_str = json.dumps(events, indent=2, ensure_ascii=False)
            prompt_vars["event_log"] = event_log_str
            prompt_vars["away_time_seconds"] = config.get("away_time_seconds", 0)
            prompt_vars["total_time_seconds"] = config.get("total_time_seconds", 0)
            prompt_vars["focus_time_seconds"] = config.get("focus_time_seconds", 0)
        else:
            prompt_vars["event_log"] = "события не зафиксированы"
            prompt_vars["away_time_seconds"] = 0
            prompt_vars["total_time_seconds"] = 0
            prompt_vars["focus_time_seconds"] = 0

        try:
            full_prompt = custom_prompt.format(**prompt_vars)
            # Также форматируем дополнительные промпты, так как они могут содержать {event_log} и др.
            if extra_prompts:
                try:
                    extra_prompts = extra_prompts.format(**prompt_vars)
                except Exception:  # nosec B110
                    # Если не удалось отформатировать доп. промпт, оставляем как есть
                    # Мы не логируем это как ошибку, так как это допустимое поведение для некоторых шаблонов
                    pass
        except KeyError as e:
            # Если в промпте есть лишние скобки или переменные, которых нет в vars, 
            # пробуем хотя бы базовые заменить
            full_prompt = custom_prompt.replace("{question}", question).replace("{reference_answer}", reference_answer).replace("{student_answer}", student_answer)

        # 4. Внедрение доп. промптов и обновление JSON-формата
        # Ищем блок JSON в промпте, чтобы вставить поля туда
        if json_extras:
            # Пытаемся вставить инструкции анти-чита перед блоком JSON или в конец
            # Проверяем несколько вариантов маркеров начала формата ответа
            markers = ["Верни ответ ТОЛЬКО в формате JSON", "ФОРМАТ ОТВЕТА", "JSON:", "```json"]
            marker_found = False
            for marker in markers:
                if marker in full_prompt:
                    # Вставляем доп. инструкции ПЕРЕД маркером формата
                    idx = full_prompt.find(marker)
                    full_prompt = full_prompt[:idx] + "\n## АНТИ-ЧИТ ПРОВЕРКА\n" + extra_prompts + "\n\n" + full_prompt[idx:]
                    marker_found = True
                    break
            
            if not marker_found:
                full_prompt += "\n## АНТИ-ЧИТ ПРОВЕРКА\n" + extra_prompts
            
            # Обновляем сам JSON шаблон (вставляем поля перед последней закрывающей скобкой)
            # Мы ищем последнюю скобку ПРЕЖДЕ чем мы могли добавить что-то еще в конец (хотя мы теперь вставляем перед маркером)
            if '"feedback":' in full_prompt:
                # Ищем последнюю закрывающую скобку
                last_brace_idx = full_prompt.rfind('}')
                if last_brace_idx != -1:
                    full_prompt = full_prompt[:last_brace_idx].strip()
                    if full_prompt.endswith(','): full_prompt = full_prompt[:-1]
                    full_prompt += json_extras + "\n}"
        
        return full_prompt

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
        
        prompt = self._prepare_full_prompt(question, reference_answer, student_answer, criteria, config)

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


class OpenAICompatibleProvider(YandexGPTProvider):
    """
    Универсальный провайдер для OpenAI-совместимых API (DeepSeek, Qwen)
    """
    
    def __init__(self, base_url: str, default_model: str, api_key_name: str):
        self.base_url = base_url
        self.default_model = default_model
        self.api_key_name = api_key_name

    async def evaluate_answer(
        self,
        question: str,
        reference_answer: str,
        student_answer: str,
        criteria: Dict[str, int],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        import httpx
        config = config or {}
        
        # Получаем API ключ из настроек или конфига
        api_key = config.get(self.api_key_name) or getattr(settings, self.api_key_name.upper(), None)
        model = config.get("model") or self.default_model
        
        if not api_key:
            return {
                "criteria_scores": {k: 0 for k in criteria.keys()},
                "total_score": 0,
                "feedback": f"API key {self.api_key_name} not configured"
            }

        criteria_template = ",\n    ".join([f'"{k}": <баллы>' for k in criteria.keys()])
        prompt = f"""Ты — эксперт-преподаватель медицины. Оцени ответ студента по критериям.
            
ВОПРОС: {question}
ЭТАЛОН: {reference_answer}
ОТВЕТ СТУДЕНТА: {student_answer}

КРИТЕРИИ:
{self._format_criteria(criteria)}

Верни ответ ТОЛЬКО в формате JSON:
{{
  "criteria_scores": {{
    {criteria_template}
  }},
  "total_score": <сумма>,
  "feedback": "<текст>"
}}"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "Ты эксперт-преподаватель медицины. Отвечай СТРОГО в формате JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=60.0
                )
                
                if response.status_code != 200:
                    raise Exception(f"API Error: {response.status_code} {response.text}")
                
                result_text = response.json()["choices"][0]["message"]["content"]
                return self._parse_json_response(result_text)
                
        except Exception as e:
            logger.error(f"Provider {self.default_model} error: {e}")
            return {
                "criteria_scores": {k: 0 for k in criteria.keys()},
                "total_score": 0,
                "feedback": f"Error: {str(e)}"
            }


class GigaChatProvider(YandexGPTProvider):
    """
    GigaChat Provider
    """
    
    def __init__(self):
        self.token = None
        self.default_model = "GigaChat:latest"

    async def _get_token(self, credentials: str, scope: str):
        import httpx
        import uuid
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={
                    "Authorization": f"Basic {credentials}",
                    "RqUID": str(uuid.uuid4()),
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={"scope": scope}
            )
            if response.status_code != 200:
                raise Exception(f"GigaChat Auth Error: {response.text}")
            return response.json()["access_token"]

    async def evaluate_answer(
        self,
        question: str,
        reference_answer: str,
        student_answer: str,
        criteria: Dict[str, int],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        import httpx
        config = config or {}
        credentials = config.get("gigachat_credentials") or settings.GIGACHAT_CREDENTIALS
        scope = config.get("gigachat_scope") or settings.GIGACHAT_SCOPE
        
        if not credentials:
            return {"criteria_scores": {}, "total_score": 0, "feedback": "GigaChat credentials not configured"}

        try:
            token = await self._get_token(credentials, scope)
            
            criteria_template = ",\n    ".join([f'"{k}": <баллы>' for k in criteria.keys()])
            prompt = f"""Оцени ответ студента по медицине.
Вопрос: {question}
Эталон: {reference_answer}
Ответ: {student_answer}
Критерии: {self._format_criteria(criteria)}
Верни JSON: {{"criteria_scores": {{{criteria_template}}}, "total_score": 0, "feedback": ""}}"""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "model": self.default_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1
                    }
                )
                result_text = response.json()["choices"][0]["message"]["content"]
                return self._parse_json_response(result_text)
        except Exception as e:
            return {"criteria_scores": {}, "total_score": 0, "feedback": f"GigaChat Error: {str(e)}"}


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
            "yandex": YandexGPTProvider(),
            "gigachat": GigaChatProvider(),
            "deepseek": OpenAICompatibleProvider(
                base_url="https://api.deepseek.com",
                default_model="deepseek-chat",
                api_key_name="deepseek_api_key"
            ),
            "qwen": OpenAICompatibleProvider(
                base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                default_model="qwen-plus",
                api_key_name="qwen_api_key"
            )
        }
    
    def get_provider(self, strategy: str, priority: str = "normal", config: Optional[Dict[str, Any]] = None) -> BaseLLMProvider:
        """
        Выбор провайдера по стратегии
        
        Args:
            strategy: local | hybrid | yandex | gigachat | deepseek | qwen
            priority: "critical" для важных задач, "normal" для обычных
            config: словарь настроек из БД
        """
        if strategy in self.providers:
            return self.providers[strategy]
        
        if strategy == "hybrid":
            # Гибридная логика: Облако как основной, Локальный как fallback
            # (Логика fallback реализована в LLMService.evaluate_text_answer)
            cloud_strategy = (config or {}).get("hybrid_cloud_provider") or "deepseek"
            return self.providers.get(cloud_strategy, self.providers["deepseek"])
        
        # Fallback
        default_strategy = settings.LLM_STRATEGY
        return self.providers.get(default_strategy, self.providers["yandex"])


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
    
    async def generate_test_code(
        self,
        file_content: str,
        file_path: str,
        db: Optional[AsyncSession] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Генерация кода теста для указанного файла на основе его содержимого
        """
        db_config = config
        if db_config is None and db:
            db_config = await self._get_db_config(db)
        
        db_config = (db_config or {}).copy()
        strategy = db_config.get("strategy") or settings.LLM_STRATEGY
        provider = self.router.get_provider(strategy, config=db_config)

        prompt = f"""Ты — эксперт по автоматизированному тестированию. 
Напиши качественный, готовый к выполнению тест для следующего файла: `{file_path}`.

СОДЕРЖИМОЕ ФАЙЛА:
{file_content}

ТРЕБОВАНИЯ:
1. Используй {'pytest' if file_path.endswith('.py') else 'vitest'}.
2. Покрывай основные функции и пограничные случаи.
3. Верни ТОЛЬКО чистый код теста без markdown-разметки (без ```).
4. Импортируй все необходимые зависимости.
5. Если это React-компонент, используй react-testing-library.
"""

        try:
            # Используем провайдер напрямую для генерации (через внутренний метод подготовки промпта если нужно, 
            # или просто вызвав completion если бы он был открыт. 
            # В текущей реализации мы можем адаптировать запрос.)
            
            # Так как у нас провайдеры заточены под evaluate_answer, 
            # добавим им поддержку универсального запроса или используем существующий.
            # Для простоты, мы можем временно пропатчить вызов или расширить провайдеры.
            
            # Но самый чистый путь - добавить метод в BaseLLMProvider
            if hasattr(provider, 'generate_completion'):
                 return await provider.generate_completion(prompt, db_config)
            else:
                # Если нет специального метода, попробуем использовать логику вызова API напрямую
                # Для YandexGPT это будет:
                if isinstance(provider, YandexGPTProvider):
                    return await self._call_yandex_directly(prompt, db_config)
                return "# LLM Provider does not support general generation yet"
        except Exception as e:
            logger.error(f"Error generating test code: {e}")
            return f"# Error during generation: {str(e)}"

    async def _call_yandex_directly(self, prompt: str, config: Dict[str, Any]) -> str:
        import httpx
        api_key = config.get("yandex_api_key") or settings.YANDEX_API_KEY
        folder_id = config.get("yandex_folder_id") or settings.YANDEX_FOLDER_ID
        
        if not api_key or not folder_id:
            return "# YandexGPT API Key or Folder ID is missing. Check your .env file."
            
        model_name = "yandexgpt/latest"
        
        auth_header = f"Api-Key {api_key}"
        if api_key and api_key.startswith("t1."):
            auth_header = f"Bearer {api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                headers={"Authorization": auth_header, "x-folder-id": folder_id},
                json={
                    "modelUri": f"gpt://{folder_id}/{model_name}",
                    "completionOptions": {"stream": False, "temperature": 0.2, "maxTokens": 4000},
                    "messages": [
                        {"role": "system", "text": "Ты помощник-программист, который пишет тесты."},
                        {"role": "user", "text": prompt}
                    ]
                },
                timeout=90.0
            )
            if response.status_code == 200:
                return response.json()["result"]["alternatives"][0]["message"]["text"].strip()
            return f"# API Error: {response.status_code}"

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
        Оценка текстового ответа с поддержкой fallback и анти-чита
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
        
        db_config = (db_config or {}).copy()
        
        # --- Анти-чит логика ---
        manual_integrity_score = 1.0
        plagiarism_score = db_config.get("plagiarism_score", 0.0)
        
        # Предварительная проверка на плагиат (если найден через Search API)
        if plagiarism_score > 0.5:
            # Если найден плагиат, сильно снижаем целостность сразу
            manual_integrity_score = min(manual_integrity_score, 0.2)

        strategy = db_config.get("strategy") or settings.LLM_STRATEGY
        
        # 1. Первая попытка
        provider = self.router.get_provider(strategy, priority, db_config)
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
                
            # Применяем integrity_score из ответа LLM или наш manual
            # Если в конфиге были промпты анти-чита, LLM должна была вернуть integrity_score
            llm_integrity = result.get("integrity_score")
            final_integrity = llm_integrity if llm_integrity is not None else manual_integrity_score
            
            # --- Расширенная логика штрафов на основе порогов ---
            ai_threshold_error = db_config.get("ai_threshold_error", 0.8)
            plagiarism_threshold = db_config.get("plagiarism_threshold", 0.5)
            integrity_threshold_error = db_config.get("integrity_threshold_error", 0.6)
            
            ai_prob = result.get("ai_probability") or result.get("ai_score") or 0.0
            is_plagiarism = plagiarism_score > plagiarism_threshold
            
            # Проктор теперь оценивается самой LLM (final_integrity)
            # Мы считаем критическим нарушением если:
            # 1. Плагиат обнаружен (is_plagiarism)
            # 2. Вероятность ИИ критическая (ai_prob >= ai_threshold_error)
            # 3. Сама LLM поставила низкий балл честности (например, < integrity_threshold_error)
            
            is_critical = is_plagiarism or ai_prob >= ai_threshold_error or final_integrity <= integrity_threshold_error
            
            if final_integrity < 1.0 or is_critical:
                # Определяем итоговый коэффициент штрафа
                # Если критично — балл обнуляется (0)
                # Если просто подозрительно — используем integrity_score
                penalty_factor = final_integrity
                if is_critical:
                    penalty_factor = 0.0
                
                reduction_percent = round((1.0 - penalty_factor) * 100)
                
                if reduction_percent > 0:
                    result["total_score"] = result["total_score"] * penalty_factor
                    
                    reasons = []
                    if is_plagiarism: reasons.append("Плагиат")
                    if ai_prob >= ai_threshold_error: reasons.append(f"Использование ИИ: {ai_prob:.2f}")
                    if final_integrity <= integrity_threshold_error: reasons.append(f"Списывание: {final_integrity:.2f}")
                    elif final_integrity < 1.0: reasons.append(f"Подозрительное поведение: {final_integrity:.2f}")
                    
                    percent_text = "100%" if is_critical else f"{reduction_percent}%"
                    header = f"Нарушение: Оценка снижена на {percent_text}"
                    penalty_note = f"{header}\nПричины:\n" + "\n".join(reasons)
                else:
                    penalty_note = ""
            else:
                penalty_note = ""
            
            result["integrity_score"] = final_integrity
            result["ai_probability"] = ai_prob
            result["plagiarism_found"] = is_plagiarism
            result["penalty_note"] = penalty_note
            result["provider"] = provider.__class__.__name__
            return result

        except Exception as e:
            logger.warning(f"Primary LLM provider ({provider.__class__.__name__}) failed: {e}")
            
            # 2. Попытка через запасной вариант (Локальная модель)
            # Если мы уже на локальной модели, пробуем Яндекс как последний шанс
            fallback_strategy = "local" if strategy != "local" else "yandex"
            fallback_provider = self.router.get_provider(fallback_strategy, priority, db_config)
            
            logger.info(f"Attempting fallback to {fallback_provider.__class__.__name__}")
            
            try:
                result = await fallback_provider.evaluate_answer(
                    question=question,
                    reference_answer=reference_answer,
                    student_answer=student_answer,
                    criteria=criteria,
                    config=db_config
                )
                
                # Применяем integrity_score к итоговому баллу в fallback
                llm_integrity = result.get("integrity_score")
                final_integrity = llm_integrity if llm_integrity is not None else manual_integrity_score

                # --- Расширенная логика штрафов на основе порогов (Fallback) ---
                ai_threshold_error = db_config.get("ai_threshold_error", 0.8)
                plagiarism_threshold = db_config.get("plagiarism_threshold", 0.5)
                integrity_threshold_error = db_config.get("integrity_threshold_error", 0.6)
                
                ai_prob = result.get("ai_probability") or result.get("ai_score") or 0.0
                is_plagiarism = plagiarism_score > plagiarism_threshold

                is_critical = is_plagiarism or ai_prob >= ai_threshold_error or final_integrity <= integrity_threshold_error

                if final_integrity < 1.0 or is_critical:
                    penalty_factor = final_integrity
                    if is_critical:
                        penalty_factor = 0.0
                    
                    reduction_percent = round((1.0 - penalty_factor) * 100)
                    
                    if reduction_percent > 0:
                        result["total_score"] = result["total_score"] * penalty_factor
                        
                        reasons = []
                        if is_plagiarism: reasons.append("Плагиат")
                        if ai_prob >= ai_threshold_error: reasons.append(f"Использование ИИ: {ai_prob:.2f}")
                        if final_integrity <= integrity_threshold_error: reasons.append(f"Списывание: {final_integrity:.2f}")
                        elif final_integrity < 1.0: reasons.append(f"Подозрительное поведение: {final_integrity:.2f}")
                        
                        percent_text = "100%" if is_critical else f"{reduction_percent}%"
                        header = f"Нарушение: Оценка снижена на {percent_text}"
                        penalty_note = f"{header}\nПричины:\n" + "\n".join(reasons)
                    else:
                        penalty_note = ""
                else:
                    penalty_note = ""
                
                result["integrity_score"] = final_integrity
                result["ai_probability"] = ai_prob
                result["plagiarism_found"] = is_plagiarism
                result["penalty_note"] = penalty_note
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

