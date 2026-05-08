"""
Проверка нескольких API-ключей Yandex GPT из окружения (без секретов в репозитории).

Переменные:
  YANDEX_FOLDER_ID — каталог Yandex Cloud
  YANDEX_API_KEY_TEST_<имя>=<ключ> — любое число пар (например YANDEX_API_KEY_TEST_main)
  либо только YANDEX_API_KEY — один ключ с именем default
"""
from __future__ import annotations

import asyncio
import os

import httpx
from dotenv import load_dotenv

load_dotenv("backend/.env")


def _collect_keys() -> dict[str, str]:
    prefix = "YANDEX_API_KEY_TEST_"
    out: dict[str, str] = {}
    for name, val in os.environ.items():
        if name.startswith(prefix) and val.strip():
            out[name[len(prefix) :]] = val.strip()
    single = os.getenv("YANDEX_API_KEY", "").strip()
    if not out and single:
        out["default"] = single
    return out


folder_id = os.getenv("YANDEX_FOLDER_ID", "").strip()


async def test_key(name: str, api_key: str) -> None:
    preview = f"{api_key[:10]}..." if len(api_key) > 10 else "(empty)"
    print(f"Testing key: {name} ({preview})")
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {api_key}",
        "x-folder-id": folder_id,
    }
    data = {
        "modelUri": f"gpt://{folder_id}/yandexgpt-lite/latest",
        "completionOptions": {"stream": False, "temperature": 0.1, "maxTokens": 50},
        "messages": [{"role": "user", "text": "Hi"}],
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data, timeout=10.0)
            print(f"Result {name}: {response.status_code}")
            if response.status_code == 200:
                print(f"SUCCESS with {name}!")
            else:
                print(f"Error {name}: {response.text}")
    except Exception as e:
        print(f"Exception {name}: {e}")


async def main() -> None:
    keys = _collect_keys()
    if not folder_id:
        print("Set YANDEX_FOLDER_ID in backend/.env or environment.")
        return
    if not keys:
        print(
            "No keys: set YANDEX_API_KEY or YANDEX_API_KEY_TEST_<name> in backend/.env."
        )
        return
    for name, key in keys.items():
        await test_key(name, key)
        print("-" * 10)


if __name__ == "__main__":
    asyncio.run(main())
