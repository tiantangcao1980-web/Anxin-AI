"""诊断智能对话 mock 响应问题"""
import asyncio
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.database import async_session_maker
from src.models.llm_config import LLMConfig
from src.services.llm_service import LLMService
from sqlalchemy import select

async def diagnose():
    async with async_session_maker() as session:
        # 1. 检查数据库中的配置
        result = await session.execute(select(LLMConfig))
        configs = result.scalars().all()
        
        print("=" * 60)
        print("数据库 LLM 配置诊断")
        print("=" * 60)
        
        if not configs:
            print("!! 数据库中没有任何 LLM 配置 !!")
            return
        
        for c in configs:
            print(f"\n--- Config: {c.name} ---")
            print(f"  Provider: {c.provider}")
            print(f"  Model: {c.model_name}")
            print(f"  Base URL: {c.api_base_url}")
            print(f"  Active: {c.is_active}")
            print(f"  Default: {c.is_default}")
            
            # 尝试解密 Key
            if c.api_key:
                print(f"  Encrypted Key: {c.api_key[:20]}...")
                try:
                    decrypted = LLMService.decrypt_api_key(c.api_key)
                    if decrypted and decrypted != c.api_key:
                        print(f"  Decrypted Key: {decrypted[:8]}...{decrypted[-4:]}")
                        is_valid = len(decrypted) > 10 and not decrypted.startswith("Z0FBQU")
                        print(f"  Key valid: {is_valid}")
                    else:
                        print(f"  !! DECRYPTION FAILED (returned same value) !!")
                except Exception as e:
                    print(f"  !! DECRYPTION ERROR: {e} !!")
            else:
                print(f"  !! NO API KEY SET !!")
        
        # 2. 检查 .env 中的默认配置
        print("\n" + "=" * 60)
        print("环境变量 LLM 配置 (.env)")
        print("=" * 60)
        from src.core.config import settings
        print(f"  Provider: {settings.LLM_PROVIDER}")
        print(f"  Model: {settings.LLM_MODEL}")
        print(f"  Base URL: {settings.LLM_BASE_URL}")
        print(f"  API Key: {settings.LLM_API_KEY[:10]}..." if settings.LLM_API_KEY else "  API Key: EMPTY")
        is_dummy = "dummy" in settings.LLM_API_KEY
        print(f"  Is Dummy Key: {is_dummy}")
        
        # 3. 模拟 ChatService 的配置加载逻辑
        print("\n" + "=" * 60)
        print("ChatService._load_llm_config() 模拟")
        print("=" * 60)
        
        llm_config = await LLMService.get_default_config(session)
        if llm_config:
            print(f"  Loaded default config: {llm_config.name}")
            print(f"  Provider: {llm_config.provider}")
            print(f"  Model: {llm_config.model_name}")
        else:
            # Fallback
            result2 = await session.execute(
                select(LLMConfig)
                .where(LLMConfig.config_type == "llm")
                .where(LLMConfig.is_active == True)
                .order_by(LLMConfig.updated_at.desc())
                .limit(1)
            )
            llm_config = result2.scalar_one_or_none()
            if llm_config:
                print(f"  Fallback config: {llm_config.name}")
            else:
                print(f"  !! NO CONFIG FOUND - will use .env defaults (dummy key!) !!")
        
        # 4. 模拟 Agent 的配置解析
        if llm_config:
            print("\n" + "=" * 60)
            print("Agent._prepare_llm_request() 模拟")
            print("=" * 60)
            
            api_key = llm_config.api_key or ""
            api_base_url = llm_config.api_base_url or ""
            model_name = llm_config.model_name
            
            # 解密
            if api_key and not api_key.startswith("sk-") and len(api_key) > 20:
                try:
                    decrypted = LLMService.decrypt_api_key(api_key)
                    api_key = decrypted
                except:
                    pass
            
            print(f"  Final API Key: {api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else f"  Final API Key: {api_key}")
            print(f"  Base URL: {api_base_url}")
            print(f"  Model: {model_name}")
            
            is_dummy = "dummy" in api_key or not api_key
            print(f"  Is Dummy: {is_dummy}")
            
            if is_dummy:
                print("\n  >> 这就是 mock 响应的原因! API Key 无效或为空 <<")
            
            base_url = api_base_url.rstrip("/")
            if not base_url.endswith("/chat/completions") and not base_url.endswith("/v1"):
                url = f"{base_url}/chat/completions"
            elif base_url.endswith("/v1"):
                url = f"{base_url}/chat/completions"
            else:
                url = base_url
            print(f"  Final URL: {url}")

asyncio.run(diagnose())
