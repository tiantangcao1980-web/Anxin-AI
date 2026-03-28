import asyncio
import sys
import os
from unittest.mock import MagicMock, patch
import types

# Add src to python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

# Mock logger to avoid clutter
with patch('loguru.logger'):
    from src.agents.workforce import LegalWorkforce
    from src.agents.base import BaseLegalAgent, AgentConfig

async def mock_chat(self, message: str) -> str:
    """Mock chat response based on agent name"""
    print(f"[Mock] Agent {self.name} received message: {message[:50]}...")
    
    if "协调调度" in self.name:
        # Coordinator return JSON plan
        return """
        {
          "analysis": "User wants to review a contract.",
          "plan": [
            {
              "id": "task_1",
              "agent": "contract_reviewer",
              "instruction": "Review the contract for risks.",
              "depends_on": []
            }
          ],
          "reasoning": "Standard review process.",
          "priority": "normal",
          "total_steps": 1
        }
        """
    elif "合同审查" in self.name:
        # Contract Reviewer return JSON result
        return """
        {
            "summary": "This is a risky contract.",
            "risk_level": "high",
            "risk_score": 0.8,
            "risks": [{"type": "legal", "level": "high", "title": "Bad clause", "description": "Clause 1 is bad", "suggestion": "Fix it"}],
            "suggestions": ["Don't sign"]
        }
        """
    elif "共识" in self.name:
         return """
         {
            "final_decision": "Contract is High Risk. Do not sign.",
            "risk_level": "high",
            "is_consensus_reached": true
         }
         """
    else:
        return "I am a mocked agent."

async def main():
    print("Starting Workforce Verification...")

    # Mock get_llm_config_sync to avoid DB calls
    with patch('src.agents.base.get_llm_config_sync') as mock_config:
        mock_config.return_value = MagicMock(
            provider="openai",
            model_name="gpt-4o",
            api_key="sk-mock",
            api_base_url="https://mock.api"
        )
        
        # Monkey patch BaseLegalAgent.chat
        BaseLegalAgent.chat = mock_chat
        # Avoid ModelFactory creation failing
        BaseLegalAgent._init_agent = lambda self: None 

        workforce = LegalWorkforce()
        print("Workforce initialized.")
        
        task_desc = "请帮我审查这份买卖合同，有没有风险？"
        print(f"Submitting task: {task_desc}")
        
        result = await workforce.process_task(task_desc)
        
        print("\n--- Execution Result ---")
        print(f"Task: {result['task']}")
        print(f"Analysis: {result['analysis']['analysis']}")
        print(f"Final Result Summary: {result['final_result']['summary']}")
        print("--- Verification Completed ---")

if __name__ == "__main__":
    asyncio.run(main())
