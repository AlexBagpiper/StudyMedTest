
import asyncio
import json
import uuid
import os
from app.services.llm_service import llm_service

async def run_anticheat_direct_test():
    # Load custom prompt from DB backup
    with open("llm_config.json", "r", encoding="utf-8") as f:
        db_config = json.load(f)
    
    question = "Тестовый вопрос про античит. Что такое аспирин?"
    reference = "Аспирин - это ацетилсалициловая кислота, НПВС."
    student_answer = "Аспирин это лекарство."
    
    events_mock = [{"type": "paste_attempted", "time": f"2026-02-13T04:02:{i:02d}.000Z"} for i in range(10)]

    
    config = {
        "ai_check_enabled": True,
        "event_log": events_mock,
        "yandex_api_key": db_config.get("yandex_api_key"),
        "yandex_folder_id": db_config.get("yandex_folder_id"),
        "strategy": "yandex",
        "evaluation_prompt": db_config.get("evaluation_prompt"),
        "ai_check_prompt": db_config.get("ai_check_prompt"),
        "integrity_check_prompt": db_config.get("integrity_check_prompt")
    }
    
    criteria = {
        "factual_correctness": 40,
        "completeness": 30,
        "terminology": 20,
        "structure": 10
    }
    
    print("Testing LLM directly with fixed code and custom prompt...")
    result = await llm_service.evaluate_text_answer(
        question=question,
        reference_answer=reference,
        student_answer=student_answer,
        criteria=criteria,
        config=config
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    if result.get("integrity_score", 1.0) < 1.0:
        print("\nSUCCESS: Fixed code detected the behavior and penalized the score.")
    else:
        print("\nFAILURE: Fixed code did NOT penalize the score.")

if __name__ == "__main__":
    asyncio.run(run_anticheat_direct_test())
