"""端到端测试：检查 Key 解密 + 直接调用 LLM API"""
import asyncio, sys, os, httpx
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.database import async_session_maker
from src.models.llm_config import LLMConfig
from src.services.llm_service import LLMService
from sqlalchemy import select

async def test():
    async with async_session_maker() as session:
        # 1. 获取所有配置
        result = await session.execute(select(LLMConfig).where(LLMConfig.is_active == True))
        configs = result.scalars().all()
        
        print("=" * 60)
        for c in configs:
            print(f"\n--- {c.name} (default={c.is_default}) ---")
            print(f"  Provider: {c.provider}")
            print(f"  Model: {c.model_name}")
            print(f"  BaseURL: {c.api_base_url}")
            print(f"  Key raw length: {len(c.api_key) if c.api_key else 0}")
            
            if not c.api_key:
                print("  !! KEY IS EMPTY - user hasn't saved a key yet !!")
                continue
            
            # 尝试解密
            raw_key = c.api_key
            print(f"  Key first 20 chars: {raw_key[:20]}")
            
            try:
                decrypted = LLMService.decrypt_api_key(raw_key)
                if decrypted == raw_key:
                    print("  Decrypt returned same value (might be plaintext or failed)")
                    final_key = raw_key
                else:
                    print(f"  Decrypted OK: {decrypted[:8]}...{decrypted[-4:]}")
                    final_key = decrypted
            except Exception as e:
                print(f"  Decrypt error: {e}")
                final_key = raw_key
            
            # 直接调用 API 测试
            print(f"\n  Testing API call...")
            base = c.api_base_url.rstrip("/")
            url = f"{base}/chat/completions"
            headers = {
                "Authorization": f"Bearer {final_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": c.model_name,
                "messages": [{"role": "user", "content": "hello"}],
                "max_tokens": 10,
            }
            
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    print(f"  HTTP Status: {resp.status_code}")
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        print(f"  Response: {content[:100]}")
                        print(f"  >> SUCCESS! LLM API is working! <<")
                    else:
                        print(f"  Error body: {resp.text[:200]}")
            except Exception as e:
                print(f"  API call error: {e}")

asyncio.run(test())
