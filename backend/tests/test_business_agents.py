import pytest
from src.agents.tax_compliance import TaxComplianceAgent
from src.agents.labor_compliance import LaborComplianceAgent
from src.agents.evidence_analyst import EvidenceAnalystAgent

@pytest.mark.asyncio
async def test_tax_compliance_init():
    agent = TaxComplianceAgent()
    assert agent.name == "财税合规Agent"
    assert "tax_law_search" in agent.config.tools

@pytest.mark.asyncio
async def test_labor_compliance_init():
    agent = LaborComplianceAgent()
    assert agent.name == "劳动合规Agent"
    assert "labor_law_search" in agent.config.tools

@pytest.mark.asyncio
async def test_evidence_analyst_init():
    agent = EvidenceAnalystAgent()
    assert agent.name == "证据分析Agent"
    assert "ocr_tool" in agent.config.tools

# Simple mock test for evidence processing
@pytest.mark.asyncio
async def test_evidence_processing():
    agent = EvidenceAnalystAgent()
    # Mock chat
    async def mock_chat(msg):
        return "Mock evidence analysis"
    agent.chat = mock_chat
    
    response = await agent.process({
        "description": "Analyze this image",
        "context": {
            "evidence_files": [
                {"type": "image", "name": "contract.png", "content": "base64..."}
            ]
        }
    })
    
    assert response.agent_name == "证据分析Agent"
    assert response.actions[0]["type"] == "evidence_processing"
    # Ensure the prompt generation logic (which runs before chat) didn't crash
    # We can't easily check the prompt content without mocking chat details more deeply, 
    # but successful execution implies the prompt formatting logic worked.
