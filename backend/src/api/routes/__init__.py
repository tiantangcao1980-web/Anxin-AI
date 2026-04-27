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
from src.api.routes import rtc
from src.api.routes import sync, updates, offline_packs, privacy
from src.api.routes import metrics
from src.api.routes import knowledge_management
from src.api.routes import harness
from src.api.routes import cli
from src.api.routes import security_challenge
from src.api.routes import case_market
from src.api.routes import agent_tasks
from src.api.routes import im_pairing
from src.api.routes import app_authorizations
from src.api.routes import skills
<<<<<<< HEAD
from src.api.routes import fetch
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
from src.api.routes import personas
=======
from src.api.routes import persona_market
>>>>>>> 94b6f50 (feat(p7-market-researcher): 市场研究员 persona + DeepResearch 迭代算法 + 5 API)
=======
from src.api.routes import fetch, persona_sales
>>>>>>> 071b039 (feat(p7-lead-hunter): 获客猎手 persona + 5 capabilities + LeadScoring + 6 API)
=======
from src.api.routes import persona_content
>>>>>>> 8258c91 (feat(p7-content-director): 内容总监 persona + 5 capabilities + 7 API)
=======
from src.api.routes import persona_ecommerce  # P7-E
>>>>>>> b3b882f (feat(p7-ecommerce-assistant): 跨境电商助手 persona + 6 capabilities + AI 议价 + 7 API)

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(security_challenge.router, prefix="/auth", tags=["安全挑战"])
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
api_router.include_router(rtc.router, prefix="/rtc", tags=["音视频通话"])
api_router.include_router(sync.router, prefix="/sync", tags=["客户端同步"])
api_router.include_router(updates.router, prefix="/updates", tags=["OTA更新"])
api_router.include_router(offline_packs.router, prefix="/offline-packs", tags=["离线数据包"])
api_router.include_router(privacy.router, prefix="/privacy", tags=["隐私与 DSAR"])
api_router.include_router(metrics.router, tags=["监控指标"])
api_router.include_router(knowledge_management.router, tags=["知识管理"])
api_router.include_router(harness.router, tags=["Harness监控"])
api_router.include_router(cli.router, tags=["CLI命令"])
api_router.include_router(case_market.router, tags=["案源市场"])
api_router.include_router(agent_tasks.router, prefix="/agent-tasks", tags=["异步任务"])
api_router.include_router(im_pairing.router, prefix="/im/pairing", tags=["IM配对授权"])
api_router.include_router(app_authorizations.router, prefix="/app-authorizations", tags=["应用授权"])
api_router.include_router(skills.router, prefix="/skills", tags=["技能注册表"])
api_router.include_router(fetch.router, prefix="/fetch", tags=["信息获取栈"])
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
api_router.include_router(personas.router, prefix="/personas", tags=["V3 Personas"])
=======
api_router.include_router(persona_market.router, prefix="/personas/market", tags=["市场研究员"])
>>>>>>> 94b6f50 (feat(p7-market-researcher): 市场研究员 persona + DeepResearch 迭代算法 + 5 API)
=======
api_router.include_router(persona_sales.router, prefix="/personas/sales", tags=["获客猎手"])
>>>>>>> 071b039 (feat(p7-lead-hunter): 获客猎手 persona + 5 capabilities + LeadScoring + 6 API)
=======
api_router.include_router(persona_content.router, prefix="/personas/content", tags=["内容总监 persona"])
>>>>>>> 8258c91 (feat(p7-content-director): 内容总监 persona + 5 capabilities + 7 API)
=======
api_router.include_router(persona_ecommerce.router, prefix="/personas/ecommerce", tags=["跨境电商助手"])
>>>>>>> b3b882f (feat(p7-ecommerce-assistant): 跨境电商助手 persona + 6 capabilities + AI 议价 + 7 API)
