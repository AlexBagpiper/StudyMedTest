import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")

async def test_yandex():
    api_key = os.getenv("YANDEX_API_KEY")
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    
    print(f"Testing Yandex GPT with Folder ID: {folder_id}")
    
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {api_key}",
        "x-folder-id": folder_id
    }
    
    data = {
        "modelUri": f"gpt://{folder_id}/yandexgpt-lite/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.1,
            "maxTokens": 100
        },
        "messages": [
            {"role": "user", "text": "Привет, это тест связи."}
        ]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data, timeout=10.0)
            print(f"Yandex Response Status: {response.status_code}")
            if response.status_code == 200:
                print("Yandex GPT is working!")
                print(f"Response: {response.json()['result']['alternatives'][0]['message']['text']}")
            else:
                print(f"Yandex GPT Error: {response.text}")
    except Exception as e:
        print(f"Yandex GPT Connection Error: {e}")

async def test_local():
    local_url = os.getenv("LOCAL_LLM_URL", "http://localhost:8080")
    print(f"Testing Local LLM at: {local_url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{local_url}/chat/completions", json={
                "model": "test",
                "messages": [{"role": "user", "content": "test"}]
            }, timeout=5.0)
            print(f"Local LLM Response Status: {response.status_code}")
    except Exception as e:
        print(f"Local LLM Connection Error: {e}")

async def main():
    await test_yandex()
    print("-" * 20)
    await test_local()

if __name__ == "__main__":
    asyncio.run(main())
