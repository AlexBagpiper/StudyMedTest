
import asyncio
import json
import os
from app.services.llm_service import llm_service

async def test_llm_integrity():
    question = "Опишите клинику аппендицита."
    reference = "Боли в правой подвздошной области, симптом Щеткина-Блюмберга, тошнота, рвота."
    student_answer = "Острый аппендицит характеризуется болями, которые сначала возникают в эпигастрии, а затем смещаются в правую подвздошную область (симптом Кохера)."
    
    # Simulate multiple paste events
    event_log = [
        {"type": "paste_attempted", "time": "2026-02-13T04:02:22.163Z"},
        {"type": "paste_attempted", "time": "2026-02-13T04:02:27.096Z"}
    ]
    
    print("Testing LLM with paste events...")
    # Using keys from environment
    result = await llm_service.evaluate_text_answer(
        question=question,
        reference_answer=reference,
        student_answer=student_answer,
        config={
            "ai_check_enabled": True,
            "event_log": event_log,
            "strategy": "yandex"
        }
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(test_llm_integrity())
