import sys
import os
import importlib
from unittest.mock import MagicMock, patch

# Add src to python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

# Set dummy environment variables to avoid validation errors during import
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("LLM_API_KEY", "sk-dummy")
os.environ.setdefault("JWT_SECRET_KEY", "secret")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "admin")
os.environ.setdefault("MINIO_SECRET_KEY", "password")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "password")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

def check_agents():
    print("Checking Agents...")
    agents = [
        "src.agents.coordinator",
        "src.agents.legal_advisor",
        "src.agents.contract_reviewer",
        "src.agents.due_diligence",
        "src.agents.legal_researcher",
        "src.agents.document_drafter",
        "src.agents.compliance_officer",
        "src.agents.risk_assessor",
        "src.agents.consensus_agent",
        "src.agents.workforce",
    ]
    
    all_ok = True
    for agent_module in agents:
        print(f"Attempting to import: {agent_module}...")
        try:
            if agent_module in sys.modules:
                importlib.reload(sys.modules[agent_module])
            else:
                importlib.import_module(agent_module)
            print(f"[OK] Import success: {agent_module}")
        except Exception as e:
            print(f"[FAIL] Import failed: {agent_module}")
            print(f"Error: {e}")
            all_ok = False
    return all_ok

def check_api():
    print("\nChecking API...")
    try:
        # Pre-import src.core to ensure it's available
        import src.core
        import src.core.database
        
        # We don't need to mock create_async_engine if we don't connect,
        # but to be safe and avoid any side-effects:
        # We'll just try importing main. If it fails due to DB connection, we can mock.
        # But importing src.api.main shouldn't trigger connection, only defining routes.
        
        import src.api.main
        print("[OK] API Main import success")
        return True
    except Exception as e:
        print(f"[FAIL] API Main import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting System Integrity Check (Real Environment)...")
    
    # We silence loguru to avoid noise during import
    try:
        from loguru import logger
        logger.remove()
        logger.add(sys.stderr, level="CRITICAL")
    except ImportError:
        pass
        
    agents_ok = check_agents()
    api_ok = check_api()
    
    if agents_ok and api_ok:
        print("\n[SUCCESS] System Integrity Check Passed!")
        sys.exit(0)
    else:
        print("\n[FAILURE] System Integrity Check Failed!")
        sys.exit(1)
