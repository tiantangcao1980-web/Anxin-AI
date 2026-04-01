"""
API路由汇总
"""

from fastapi import APIRouter

from src.api.routes import auth, chat, cases, contracts, documents, due_diligence, knowledge, llm, lic, assets, notifications
from src.api.routes import sentiment, collaboration, collaboration_ws, integrations, datacenter
from src.api.routes import mcp_routes, episodic_memory
from src.api.routes import tasks, leads, experts, courses
from src.api.routes import admin
from src.api.routes import approvals
from src.api.routes import lawyer_matching
from src.api.routes import compliance
from src.api.routes import anonymous_chat
from src.api.routes import esign
from src.api.routes import payments
from src.api.routes import feature_flags
from src.api.routes import im
from src.api.routes import acquisition_analytics
from src.api.routes import firm_management
from src.api.routes import lawyer_onboarding
from src.api.routes import billing
from src.api.routes import ai_assistant
from src.api.routes import meeting_assistant

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(chat.router, prefix="/chat", tags=["AI对话"])
api_router.include_router(cases.router, prefix="/cases", tags=["案件管理"])
api_router.include_router(contracts.router, prefix="/contracts", tags=["合同审查"])
api_router.include_router(documents.router, prefix="/documents", tags=["文档管理"])
api_router.include_router(due_diligence.router, prefix="/due-diligence", tags=["尽职调查"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["知识库"])
api_router.include_router(llm.router, prefix="/llm", tags=["LLM配置"])
api_router.include_router(sentiment.router, prefix="/sentiment", tags=["舆情监控"])
api_router.include_router(collaboration.router, prefix="/collaboration", tags=["协作编辑"])
api_router.include_router(collaboration_ws.router, prefix="/collaboration", tags=["协作编辑-WebSocket"])
api_router.include_router(lic.router, prefix="/lic", tags=["LIC抓取"])
api_router.include_router(assets.router, prefix="/assets", tags=["资产管理"])
api_router.include_router(mcp_routes.router, prefix="/mcp", tags=["MCP服务"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["通知中心"])
api_router.include_router(integrations.router, prefix="/integrations/oa", tags=["OA集成"])
api_router.include_router(datacenter.router, prefix="/datacenter", tags=["企业数据中心"])
api_router.include_router(episodic_memory.router, prefix="/knowledge-center", tags=["知识中心"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务管理"])
api_router.include_router(leads.router, prefix="/leads", tags=["案源管理"])
api_router.include_router(experts.router, prefix="/experts", tags=["律师精英"])
api_router.include_router(courses.router, prefix="/courses", tags=["司法学院"])
api_router.include_router(admin.router, tags=["管理后台"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["审批流"])
api_router.include_router(lawyer_matching.router, tags=["找律师"])
api_router.include_router(compliance.router, tags=["合规自检"])
api_router.include_router(anonymous_chat.router, tags=["匿名聊天"])
api_router.include_router(esign.router, prefix="/esign", tags=["电子签章"])
api_router.include_router(payments.router, prefix="/payments", tags=["支付管理"])
api_router.include_router(feature_flags.router, tags=["功能开关"])
api_router.include_router(im.router, tags=["即时通讯"])
api_router.include_router(acquisition_analytics.router, tags=["获客分析"])
api_router.include_router(firm_management.router, tags=["律所管理"])
api_router.include_router(lawyer_onboarding.router, tags=["律师入驻"])
api_router.include_router(billing.router, tags=["计费系统"])
api_router.include_router(ai_assistant.router, tags=["AI私有助手"])
api_router.include_router(meeting_assistant.router, prefix="/assistant", tags=["AI旁听助手"])
