"""修复数据库中的 LLM 配置：清除无法解密的 Key，更新模型名称"""
import asyncio
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.database import async_session_maker
from src.models.llm_config import LLMConfig
from sqlalchemy import select

async def fix():
    async with async_session_maker() as session:
        result = await session.execute(select(LLMConfig))
        configs = result.scalars().all()
        
        for c in configs:
            print(f"Fixing: {c.name} (Provider: {c.provider})")
            
            # 清除无法解密的 Key
            if c.api_key and c.api_key.startswith("Z0FBQU"):
                print(f"  Clearing invalid encrypted key...")
                c.api_key = ""
            
            # 更新 Kimi 模型名称
            if c.name == "Kimi2.5" and c.model_name == "moonshot-v1-8k":
                print(f"  Updating model name: moonshot-v1-8k -> kimi-k2.5")
                c.model_name = "kimi-k2.5"
        
        await session.commit()
        print("\nDone! Please re-enter API keys in Settings page.")

asyncio.run(fix())
