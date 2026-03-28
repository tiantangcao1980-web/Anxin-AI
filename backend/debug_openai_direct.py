
import asyncio
import os
from openai import AsyncOpenAI
from src.core.config import settings
from src.core.llm_helper import get_llm_config_sync

# Mock config
class MockConfig:
    temperature = 0.7

async def test_direct_openai():
    print("Testing direct OpenAI call...")
    
    # Simulate _init_agent logic
    try:
        # We need env vars or mock get_llm_config_sync
        # For this test, let's just use what we know
        api_key = "sk-dummy"
        base_url = "https://api.openai.com/v1"
        model_name = "gpt-4o"
        
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=60.0,
            max_retries=3,
        )
        
        messages = [
            {"role": "system", "content": "You are a helper."},
            {"role": "user", "content": "Hello"}
        ]
        
        kwargs = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
        }
        
        print(f"Calling with kwargs: {kwargs.keys()}")
        
        # This will fail with Auth error (invalid key), but NOT "multiple values for model"
        try:
            response = await client.chat.completions.create(**kwargs)
            print("Success!")
        except Exception as e:
            print(f"Caught expected error: {e}")
            if "multiple values" in str(e):
                print("FATAL: REPRODUCED THE ERROR")
            else:
                print("Did not reproduce the error (Auth error is expected)")
                
    except Exception as e:
        print(f"Setup error: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_openai())
