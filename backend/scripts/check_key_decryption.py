import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select
from src.core.database import async_session_maker
from src.models.llm_config import LLMConfig
from src.services.llm_service import LLMService

async def check_key():
    async with async_session_maker() as session:
        result = await session.execute(select(LLMConfig).where(LLMConfig.is_active == True))
        config = result.scalars().first()
        
        if not config:
            print("No active config found.")
            return

        print(f"Checking config: {config.name}")
        print(f"Encrypted Key: {config.api_key[:10]}...")
        
        try:
            decrypted = LLMService.decrypt_api_key(config.api_key)
            print(f"Decryption SUCCESS. Key starts with: {decrypted[:5]}...")
        except Exception as e:
            print(f"Decryption FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(check_key())
