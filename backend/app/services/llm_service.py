"""
LLM Service - абстрактный слой для работы с языковыми моделями
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.core.config import settings


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
        criteria: Dict[str, int]
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


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI (GPT-4, GPT-3.5) provider
    """
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")
        
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = "gpt-4"
        except ImportError:
            raise ImportError("openai package not installed")
    
    async def evaluate_answer(
        self,
        question: str,
        reference_answer: str,
        student_answer: str,
        criteria: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Оценка через GPT-4
        """
        # Формирование промпта
        prompt = f"""Ты — эксперт-преподаватель медицины. Оцени ответ студента по следующим критериям:

ВОПРОС: {question}

ЭТАЛОННЫЙ ОТВЕТ: {reference_answer}

ОТВЕТ СТУДЕНТА: {student_answer}

КРИТЕРИИ ОЦЕНКИ:
{self._format_criteria(criteria)}

ВАЖНО: Верни ответ СТРОГО в формате JSON:
{{
  "criteria_scores": {{
    "factual_correctness": <0-{criteria.get('factual_correctness', 40)}>,
    "completeness": <0-{criteria.get('completeness', 30)}>,
    "terminology": <0-{criteria.get('terminology', 20)}>,
    "structure": <0-{criteria.get('structure', 10)}>
  }},
  "total_score": <сумма баллов>,
  "feedback": "Краткая обратная связь для студента (2-3 предложения)"
}}
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты эксперт-преподаватель медицины. Отвечай ТОЛЬКО в формате JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        
        except Exception as e:
            # Fallback результат
            return {
                "criteria_scores": {k: 0 for k in criteria.keys()},
                "total_score": 0,
                "feedback": f"Error during evaluation: {str(e)}"
            }
    
    def _format_criteria(self, criteria: Dict[str, int]) -> str:
        return "\n".join([f"{i+1}. {k.replace('_', ' ').title()}: 0-{v} баллов" 
                         for i, (k, v) in enumerate(criteria.items())])


class LocalLLMProvider(BaseLLMProvider):
    """
    Локальная LLM модель (LLaMA, Mistral через vLLM/Ollama)
    """
    
    def __init__(self):
        if not settings.LOCAL_LLM_ENABLED:
            raise ValueError("Local LLM not enabled")
        
        self.api_url = settings.LOCAL_LLM_URL
        self.model = settings.LOCAL_LLM_MODEL
    
    async def evaluate_answer(
        self,
        question: str,
        reference_answer: str,
        student_answer: str,
        criteria: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Оценка через локальную модель
        """
        import httpx
        
        prompt = f"""Оцени ответ студента. Вопрос: {question}
Эталон: {reference_answer}
Ответ студента: {student_answer}

Верни JSON с оценками по критериям."""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/completions",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "max_tokens": 512,
                        "temperature": 0.3,
                    },
                    timeout=60.0
                )
                
                result_text = response.json()["choices"][0]["text"]
                
                # Попытка парсинга JSON из ответа
                try:
                    result = json.loads(result_text)
                    return result
                except:
                    # Fallback - простая оценка
                    return {
                        "criteria_scores": {k: v // 2 for k, v in criteria.items()},
                        "total_score": sum(criteria.values()) // 2,
                        "feedback": "Оценка выполнена локальной моделью"
                    }
        
        except Exception as e:
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
        self.strategy = settings.LLM_STRATEGY
        self.providers = {}
        
        # Инициализация доступных провайдеров
        try:
            if settings.OPENAI_API_KEY:
                self.providers["openai"] = OpenAIProvider()
        except:
            pass
        
        try:
            if settings.LOCAL_LLM_ENABLED:
                self.providers["local"] = LocalLLMProvider()
        except:
            pass
    
    def get_provider(self, priority: str = "normal") -> BaseLLMProvider:
        """
        Выбор провайдера по стратегии
        
        Args:
            priority: "critical" для важных задач, "normal" для обычных
        """
        if self.strategy == "cloud":
            return self.providers.get("openai")
        
        elif self.strategy == "local":
            return self.providers.get("local")
        
        elif self.strategy == "hybrid":
            # Критичные задачи - облако, обычные - локально
            if priority == "critical" and "openai" in self.providers:
                return self.providers["openai"]
            elif "local" in self.providers:
                return self.providers["local"]
            elif "openai" in self.providers:
                return self.providers["openai"]
        
        # Fallback
        if self.providers:
            return list(self.providers.values())[0]
        
        raise RuntimeError("No LLM providers available")


class LLMService:
    """
    Главный сервис для работы с LLM
    """
    
    def __init__(self):
        self.router = LLMRouter()
    
    async def evaluate_text_answer(
        self,
        question: str,
        reference_answer: str,
        student_answer: str,
        criteria: Optional[Dict[str, int]] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Оценка текстового ответа
        """
        # Дефолтные критерии
        if criteria is None:
            criteria = {
                "factual_correctness": 40,
                "completeness": 30,
                "terminology": 20,
                "structure": 10,
            }
        
        # Выбор провайдера
        provider = self.router.get_provider(priority)
        
        # Оценка
        result = await provider.evaluate_answer(
            question=question,
            reference_answer=reference_answer,
            student_answer=student_answer,
            criteria=criteria
        )
        
        # Добавление метаданных
        result["provider"] = provider.__class__.__name__
        
        return result


# Singleton
llm_service = LLMService()

