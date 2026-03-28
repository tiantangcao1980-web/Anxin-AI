import asyncio
import sys
import os
from sqlalchemy import text

# 添加 backend 目录到 sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.database import engine, Base
from src.models import * # Import all models to ensure metadata is populated

async def reset_db():
    print("重置数据库...")
    async with engine.begin() as conn:
        # 强制删除所有表
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        print("已清空数据库Schema")
        
        # 重新创建所有表
        await conn.run_sync(Base.metadata.create_all)
        print("已重新创建所有表")

if __name__ == "__main__":
    asyncio.run(reset_db())
