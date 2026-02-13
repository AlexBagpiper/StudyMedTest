
import asyncio
import json
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.system_config import SystemConfig

async def check_config():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SystemConfig).where(SystemConfig.key == "llm_evaluation_params")
        )
        config_obj = result.scalar_one_or_none()
        if config_obj:
            with open("llm_config.json", "w", encoding="utf-8") as f:
                json.dump(config_obj.value, f, indent=2, ensure_ascii=False)
            print("Config written to llm_config.json")
        else:
            print("No llm_evaluation_params config found.")

if __name__ == "__main__":
    asyncio.run(check_config())
