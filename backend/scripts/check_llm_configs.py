import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select
from src.core.database import async_session_maker
from src.models.llm_config import LLMConfig

async def check_configs():
    async with async_session_maker() as session:
        result = await session.execute(select(LLMConfig))
        configs = result.scalars().all()
        
        print(f"Found {len(configs)} LLM configurations:")
        for c in configs:
            print(f"ID: {c.id}")
            print(f"  Name: {c.name}")
            print(f"  Provider: {c.provider}")
            print(f"  Is Default: {c.is_default}")
            print(f"  Is Active: {c.is_active}")
            print(f"  Config Type: {c.config_type}")
            print(f"  API Base: {c.api_base_url}")
            print("-" * 20)
            
        if configs and not any(c.is_default for c in configs):
            print("No default config found. Setting first active config as default...")
            first_active = next((c for c in configs if c.is_active), None)
            if first_active:
                first_active.is_default = True
                await session.commit()
                print(f"Set {first_active.name} as default.")
            else:
                print("No active config found to set as default.")

if __name__ == "__main__":
    asyncio.run(check_configs())
