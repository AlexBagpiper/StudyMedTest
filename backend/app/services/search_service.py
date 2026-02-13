"""
Сервис для проверки на плагиат через Yandex Search API
"""

import httpx
import logging
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class SearchService:
    """
    Сервис для работы с Yandex Search API (Cloud version)
    """
    
    def __init__(self):
        self.url = "https://searchapi.cloud.yandex.net/v1/search"
    
    async def check_plagiarism(self, text: str, config: Optional[Dict[str, Any]] = None) -> float:
        """
        Проверка текста на наличие в поисковой выдаче Яндекса.
        Ищет точные совпадения длинных фрагментов текста.
        
        Returns:
            float: 1.0 если плагиат найден, 0.0 если нет.
        """
        if not text or len(text.strip()) < 50:
            return 0.0
            
        config = config or {}
        api_key = config.get("yandex_search_api_key") or settings.YANDEX_SEARCH_API_KEY
        folder_id = config.get("yandex_search_folder_id") or settings.YANDEX_SEARCH_FOLDER_ID
        
        if not api_key or not folder_id:
            # Не логируем ошибку каждый раз, чтобы не спамить, если не настроено
            return 0.0

        # Очистка текста и выбор фрагмента для поиска
        clean_text = " ".join(text.split())
        # Разбиваем на предложения и выбираем самое длинное (информативное)
        sentences = [s.strip() for s in clean_text.split('.') if len(s.strip()) > 30]
        
        if not sentences:
            query = clean_text[:150]
        else:
            # Берем самое длинное предложение, но не более 200 символов (лимит Яндекса)
            query = max(sentences, key=len)[:200]

        try:
            auth_header = f"Api-Key {api_key}"
            if api_key.startswith("t1."):
                auth_header = f"Bearer {api_key}"

            async with httpx.AsyncClient() as client:
                # В Cloud API используется POST запрос с JSON
                response = await client.post(
                    self.url,
                    headers={
                        "Authorization": auth_header,
                    },
                    json={
                        "folderId": folder_id,
                        "query": f'"{query}"', # Точное совпадение в кавычках
                        "lr": [225], # Россия
                        "l10n": "ru",
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Yandex Search API error: {response.status_code} {response.text}")
                    return 0.0
                
                data = response.json()
                
                # Проверка наличия результатов. В JSON ответе Yandex Search API 
                # результаты обычно лежат в results или organic
                found = False
                
                # Проверяем типичные поля ответа
                if "results" in data and len(data["results"]) > 0:
                    found = True
                elif "organic" in data and len(data["organic"]) > 0:
                    found = True
                # Если ответ содержит xml_response (некоторые прокси так делают)
                elif "xml_response" in data:
                    if "<group>" in data["xml_response"]:
                        found = True
                
                return 1.0 if found else 0.0

        except Exception as e:
            logger.error(f"Plagiarism check failed: {str(e)}")
            return 0.0

search_service = SearchService()
