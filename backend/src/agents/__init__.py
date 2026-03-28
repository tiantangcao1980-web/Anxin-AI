"""
AI法务智能体模块

包含所有法务相关的智能体定义
"""

from src.agents.workforce import LegalWorkforce
from src.agents.legal_advisor import LegalAdvisorAgent
from src.agents.contract_reviewer import ContractReviewAgent
from src.agents.due_diligence import DueDiligenceAgent
from src.agents.legal_researcher import LegalResearchAgent
from src.agents.document_drafter import DocumentDraftAgent
from src.agents.compliance_officer import ComplianceAgent
from src.agents.risk_assessor import RiskAssessmentAgent
from src.agents.coordinator import CoordinatorAgent
from src.agents.sentiment_agent import SentimentAnalysisAgent
from src.agents.litigation_strategist import LitigationStrategistAgent
from src.agents.ip_specialist import IPSpecialistAgent
from src.agents.regulatory_monitor import RegulatoryMonitorAgent
from src.agents.tax_compliance import TaxComplianceAgent
from src.agents.labor_compliance import LaborComplianceAgent
from src.agents.evidence_analyst import EvidenceAnalystAgent
from src.agents.contract_steward import ContractStewardAgent
from src.agents.requirement_analyst import RequirementAnalystAgent

__all__ = [
    "LegalWorkforce",
    "LegalAdvisorAgent",
    "ContractReviewAgent",
    "DueDiligenceAgent",
    "LegalResearchAgent",
    "DocumentDraftAgent",
    "ComplianceAgent",
    "RiskAssessmentAgent",
    "CoordinatorAgent",
    "SentimentAnalysisAgent",
    "LitigationStrategistAgent",
    "IPSpecialistAgent",
    "RegulatoryMonitorAgent",
    "TaxComplianceAgent",
    "LaborComplianceAgent",
    "EvidenceAnalystAgent",
    "ContractStewardAgent",
    "RequirementAnalystAgent",
]
