import asyncio
import asyncpg

async def create_db():
    try:
        # Connect to default postgres database
        conn = await asyncpg.connect('postgresql://postgres:password@localhost:5433/postgres')
        
        # Terminate existing connections to the test database if any
        # (FORCE option in DROP DATABASE is available in recent Postgres versions, 
        # but let's be safe for older ones if needed, though docker is 15-alpine)
        
        print("Dropping old test database if exists...")
        try:
            await conn.execute('DROP DATABASE IF EXISTS legal_agent_test_db WITH (FORCE)')
        except Exception:
            # Fallback for older postgres or if syntax error
            await conn.execute('DROP DATABASE IF EXISTS legal_agent_test_db')
            
        print("Creating new test database...")
        await conn.execute('CREATE DATABASE legal_agent_test_db')
        
        await conn.close()
        print("Test database 'legal_agent_test_db' created successfully.")
    except Exception as e:
        print(f"Error creating test database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(create_db())
