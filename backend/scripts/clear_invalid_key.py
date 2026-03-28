import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select
from src.core.database import async_session_maker
from src.models.llm_config import LLMConfig
from src.services.llm_service import LLMService

async def clear_key():
    async with async_session_maker() as session:
        result = await session.execute(select(LLMConfig).where(LLMConfig.is_default == True))
        config = result.scalars().first()
        
        if not config:
            print("No default config found.")
            return

        print(f"Checking config: {config.name}")
        
        # Try to decrypt
        try:
            decrypted = LLMService.decrypt_api_key(config.api_key)
            if decrypted == config.api_key and len(config.api_key) > 20 and not config.api_key.startswith("sk-"):
                 # Decryption failed (returned original), and original looks encrypted (long, no sk-)
                 print("Key appears to be invalid/undecryptable. Clearing it...")
                 config.api_key = ""
                 await session.commit()
                 print("API Key cleared.")
            else:
                 print("Key seems valid or already cleared.")
        except Exception as e:
            print(f"Error checking key: {e}")

if __name__ == "__main__":
    asyncio.run(clear_key())
