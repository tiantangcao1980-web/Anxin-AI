import asyncio
import sys
import os

# 添加 backend 目录到 sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.database import init_db

if __name__ == "__main__":
    asyncio.run(init_db())
