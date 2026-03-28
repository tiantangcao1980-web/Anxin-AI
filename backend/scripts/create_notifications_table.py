
import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.database import init_db
from src.models.notification import Notification # Import to ensure it's registered in Base.metadata

if __name__ == "__main__":
    print("Initializing database to create missing tables (including notifications)...")
    asyncio.run(init_db())
    print("Done.")
