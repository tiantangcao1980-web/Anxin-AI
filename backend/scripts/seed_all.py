# -*- coding: utf-8 -*-
"""
综合种子数据脚本 - 填充所有业务表
幂等设计：重复运行不会重复插入
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime, date, timedelta
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, func


# ===== 常量 =====
ORG_ID = "00000000-0000-0000-0000-000000000001"
ADMIN_ID = "00000000-0000-0000-0000-000000000001"

# 预定义用户 ID
USER_IDS = {
    "lawyer1": "00000000-0000-0000-0000-000000000010",
    "lawyer2": "00000000-0000-0000-0000-000000000011",
    "lawyer3": "00000000-0000-0000-0000-000000000012",
    "paralegal1": "00000000-0000-0000-0000-000000000020",
    "paralegal2": "00000000-0000-0000-0000-000000000021",
}

# 预定义案件 ID
CASE_IDS = [f"00000000-0000-0000-0001-{str(i).zfill(12)}" for i in range(1, 9)]

# 预定义合同 ID
CONTRACT_IDS = [f"00000000-0000-0000-0002-{str(i).zfill(12)}" for i in range(1, 7)]

# 预定义知识库 ID
KB_IDS = [f"00000000-0000-0000-0003-{str(i).zfill(12)}" for i in range(1, 5)]

# 预定义监控 ID
MONITOR_IDS = [f"00000000-0000-0000-0004-{str(i).zfill(12)}" for i in range(1, 3)]

# 预定义计费方案 ID
PLAN_IDS = {
    "trial": "00000000-0000-0000-0006-000000000001",
    "basic": "00000000-0000-0000-0006-000000000002",
    "professional": "00000000-0000-0000-0006-000000000003",
    "enterprise": "00000000-0000-0000-0006-000000000004",
}

# 预定义团队 ID
TEAM_IDS = [f"00000000-0000-0000-0007-{str(i).zfill(12)}" for i in range(1, 5)]

# 预定义课程 ID
COURSE_IDS = [f"00000000-0000-0000-0005-{str(i).zfill(12)}" for i in range(1, 9)]


def uid():
    return str(uuid.uuid4())


async def seed():
    from src.core.database import async_session_maker, engine
    from src.models.base import Base

    # 确保表存在
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 数据库表结构同步完成")

    async with async_session_maker() as session:
        await seed_users(session)
        await session.commit()
        print("✅ 用户数据种子完成")

        await seed_cases(session)
        await session.commit()
        print("✅ 案件数据种子完成")

        await seed_documents(session)
        await session.commit()
        print("✅ 文档数据种子完成")

        await seed_contracts(session)
        await session.commit()
        print("✅ 合同数据种子完成")

        await seed_tasks(session)
        await session.commit()
        print("✅ 任务数据种子完成")

        await seed_leads(session)
        await session.commit()
        print("✅ 案源数据种子完成")

        await seed_experts(session)
        await session.commit()
        print("✅ 专家数据种子完成")

        await seed_courses(session)
        await session.commit()
        print("✅ 课程数据种子完成")

        await seed_notifications(session)
        await session.commit()
        print("✅ 通知数据种子完成")

        await seed_knowledge(session)
        await session.commit()
        print("✅ 知识库数据种子完成")

        await seed_sentiment(session)
        await session.commit()
        print("✅ 舆情数据种子完成")

        await seed_billing(session)
        await session.commit()
        print("✅ 计费套餐+订阅数据种子完成")

        await seed_firm(session)
        await session.commit()
        print("✅ 律所管理数据种子完成")

        await seed_ai_assistant(session)
        await session.commit()
        print("✅ AI助手配置数据种子完成")

    print("\n🎉 所有种子数据填充完成！")


async def check_exists(session, model, **kwargs):
    """检查记录是否已存在"""
    stmt = select(model)
    for k, v in kwargs.items():
        stmt = stmt.where(getattr(model, k) == v)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ==================== 用户 ====================
# ⚠️ 用户账号已统一由 seed_test_roles.py 管理，此处仅为业务数据关联创建兼容用户
async def seed_users(session):
    from src.models.user import User
    from src.core.security import get_password_hash

    hashed = get_password_hash("Anxin2026!Law")

    users = [
        {"id": USER_IDS["lawyer1"], "email": "lawyer.zhang@test.anxinfawu.com", "name": "张伟律师", "role": "lawyer", "user_type": "platform_lawyer"},
        {"id": USER_IDS["lawyer2"], "email": "lawyer.li@test.anxinfawu.com", "name": "李娜律师", "role": "lawyer", "user_type": "platform_lawyer"},
        {"id": USER_IDS["lawyer3"], "email": "lawyer.wang@test.anxinfawu.com", "name": "王强律师", "role": "lawyer", "user_type": "platform_lawyer"},
        {"id": USER_IDS["paralegal1"], "email": "assistant@mingde.anxinfawu.com", "name": "律师助理-刘芳", "role": "member", "user_type": "internal"},
        {"id": USER_IDS["paralegal2"], "email": "intern@mingde.anxinfawu.com", "name": "实习生-赵磊", "role": "viewer", "user_type": "internal"},
    ]

    for u in users:
        existing = await check_exists(session, User, id=u["id"])
        if not existing:
            # 检查邮箱是否已存在（可能由 seed_test_roles 创建）
            email_result = await session.execute(select(User).where(User.email == u["email"]))
            if email_result.scalar_one_or_none():
                print(f"  = 用户: {u['name']}（邮箱已存在，跳过）")
                continue
            session.add(User(
                id=u["id"], email=u["email"], name=u["name"],
                hashed_password=hashed, role=u["role"],
                user_type=u.get("user_type", "internal"),
                org_id=ORG_ID, is_active=True,
            ))
            print(f"  + 用户: {u['name']} ({u['role']})")


# ==================== 案件 ====================
async def seed_cases(session):
    from src.models.case import Case, CaseEvent, CaseStatus, CasePriority, CaseType

    cases_data = [
        {
            "id": CASE_IDS[0], "title": "XX科技公司软件开发合同纠纷",
            "case_number": "2026-民初-001", "case_type": CaseType.CONTRACT,
            "status": CaseStatus.IN_PROGRESS, "priority": CasePriority.HIGH,
            "description": "涉及标的额500万元的软件开发合同纠纷，争议焦点在于交付标准和验收流程。",
            "parties": {"client": [{"name": "XX科技发展有限公司", "role": "plaintiff"}],
                        "opponent": [{"name": "YY网络科技有限公司", "role": "defendant"}]},
            "risk_score": 0.65, "assignee_id": USER_IDS["lawyer1"],
            "deadline": datetime.now() + timedelta(days=30),
        },
        {
            "id": CASE_IDS[1], "title": "张某劳动争议仲裁案",
            "case_number": "2026-劳仲-005", "case_type": CaseType.LABOR,
            "status": CaseStatus.PENDING, "priority": CasePriority.MEDIUM,
            "description": "员工因违法解除劳动合同申请仲裁，要求支付赔偿金及未休年假工资。",
            "parties": {"client": [{"name": "张某某", "role": "applicant"}],
                        "opponent": [{"name": "ZZ贸易有限公司", "role": "respondent"}]},
            "risk_score": 0.40, "assignee_id": USER_IDS["lawyer2"],
            "deadline": datetime.now() + timedelta(days=15),
        },
        {
            "id": CASE_IDS[2], "title": "AA集团股权转让纠纷",
            "case_number": "2026-商初-012", "case_type": CaseType.CORPORATE,
            "status": CaseStatus.UNDER_REVIEW, "priority": CasePriority.URGENT,
            "description": "股权转让协议中受让方未按期支付款项，且目标公司资产存在隐瞒。标的额2000万元。",
            "parties": {"client": [{"name": "AA投资集团", "role": "plaintiff"}],
                        "opponent": [{"name": "李某某", "role": "defendant"}]},
            "risk_score": 0.82, "assignee_id": USER_IDS["lawyer1"],
            "deadline": datetime.now() + timedelta(days=60),
        },
        {
            "id": CASE_IDS[3], "title": "BB文化公司著作权侵权案",
            "case_number": "2026-知民初-008", "case_type": CaseType.INTELLECTUAL_PROPERTY,
            "status": CaseStatus.COMPLETED, "priority": CasePriority.LOW,
            "description": "被告未经许可在网络平台传播原告享有著作权的短视频作品，索赔5万元。",
            "parties": {"client": [{"name": "BB文化传播有限公司", "role": "plaintiff"}],
                        "opponent": [{"name": "CC信息技术有限公司", "role": "defendant"}]},
            "risk_score": 0.20, "assignee_id": USER_IDS["lawyer3"],
            "deadline": datetime.now() - timedelta(days=5),
            "completed_at": datetime.now() - timedelta(days=2),
        },
        {
            "id": CASE_IDS[4], "title": "DD地产公司合规审查",
            "case_number": "2026-合规-003", "case_type": CaseType.COMPLIANCE,
            "status": CaseStatus.IN_PROGRESS, "priority": CasePriority.HIGH,
            "description": "房地产开发企业年度合规审查，涉及土地使用权、预售许可、环保合规等多个领域。",
            "parties": {"client": [{"name": "DD地产开发有限公司", "role": "client"}]},
            "risk_score": 0.55, "assignee_id": USER_IDS["lawyer2"],
            "deadline": datetime.now() + timedelta(days=45),
        },
        {
            "id": CASE_IDS[5], "title": "EE医药公司收购尽职调查",
            "case_number": "2026-DD-001", "case_type": CaseType.DUE_DILIGENCE,
            "status": CaseStatus.IN_PROGRESS, "priority": CasePriority.URGENT,
            "description": "对EE医药公司的全面尽职调查，涉及知识产权、临床试验合规、合同审查等。估值3亿元。",
            "parties": {"client": [{"name": "某上市集团", "role": "acquirer"}],
                        "opponent": [{"name": "EE医药科技有限公司", "role": "target"}]},
            "risk_score": 0.70, "assignee_id": USER_IDS["lawyer1"],
            "deadline": datetime.now() + timedelta(days=20),
        },
        {
            "id": CASE_IDS[6], "title": "FF公司与供应商买卖合同纠纷",
            "case_number": "2026-民初-023", "case_type": CaseType.CONTRACT,
            "status": CaseStatus.PENDING, "priority": CasePriority.MEDIUM,
            "description": "供应商交付的原材料质量不达标，造成生产线停工，索赔80万元。",
            "parties": {"client": [{"name": "FF制造有限公司", "role": "plaintiff"}],
                        "opponent": [{"name": "GG材料科技有限公司", "role": "defendant"}]},
            "risk_score": 0.45, "assignee_id": USER_IDS["lawyer3"],
            "deadline": datetime.now() + timedelta(days=35),
        },
        {
            "id": CASE_IDS[7], "title": "某上市公司诉讼案件代理",
            "case_number": "2026-民终-009", "case_type": CaseType.LITIGATION,
            "status": CaseStatus.IN_PROGRESS, "priority": CasePriority.HIGH,
            "description": "上市公司因信息披露违规被投资者集体诉讼，涉及金额1.2亿元。",
            "parties": {"client": [{"name": "HH上市公司", "role": "defendant"}],
                        "opponent": [{"name": "投资者代表", "role": "plaintiff"}]},
            "risk_score": 0.88, "assignee_id": USER_IDS["lawyer1"],
            "deadline": datetime.now() + timedelta(days=90),
        },
    ]

    for c in cases_data:
        existing = await check_exists(session, Case, id=c["id"])
        if existing:
            continue
        session.add(Case(
            id=c["id"], title=c["title"], case_number=c["case_number"],
            case_type=c["case_type"], status=c["status"], priority=c["priority"],
            description=c["description"], parties=c["parties"],
            risk_score=c.get("risk_score"), assignee_id=c.get("assignee_id"),
            deadline=c.get("deadline"), completed_at=c.get("completed_at"),
            org_id=ORG_ID, created_by=ADMIN_ID,
        ))
        print(f"  + 案件: {c['title']}")

    # 种子案件事件
    await session.flush()  # 确保 case ID 可用

    events_data = [
        {"case_id": CASE_IDS[0], "event_type": "filing", "title": "立案受理",
         "description": "法院正式受理案件", "event_time": datetime.now() - timedelta(days=10)},
        {"case_id": CASE_IDS[0], "event_type": "hearing", "title": "第一次庭审",
         "description": "双方举证质证，法庭调查", "event_time": datetime.now() - timedelta(days=3)},
        {"case_id": CASE_IDS[1], "event_type": "mediation", "title": "调解会议",
         "description": "劳动仲裁委组织调解", "event_time": datetime.now() - timedelta(days=5)},
        {"case_id": CASE_IDS[2], "event_type": "document_review", "title": "文件审查",
         "description": "审查股权转让协议及补充协议", "event_time": datetime.now() - timedelta(days=15)},
        {"case_id": CASE_IDS[2], "event_type": "investigation", "title": "资产调查",
         "description": "对目标公司隐瞒资产进行调查取证", "event_time": datetime.now() - timedelta(days=7)},
        {"case_id": CASE_IDS[3], "event_type": "judgment", "title": "判决送达",
         "description": "法院判决原告胜诉，被告赔偿5万元", "event_time": datetime.now() - timedelta(days=2)},
        {"case_id": CASE_IDS[4], "event_type": "compliance_check", "title": "环保合规检查",
         "description": "现场检查环保设施及排放达标情况", "event_time": datetime.now() - timedelta(days=8)},
        {"case_id": CASE_IDS[5], "event_type": "due_diligence", "title": "财务尽调启动",
         "description": "进驻目标公司开展财务尽职调查", "event_time": datetime.now() - timedelta(days=12)},
        {"case_id": CASE_IDS[5], "event_type": "due_diligence", "title": "法律尽调报告初稿",
         "description": "完成法律尽调报告初稿并内部评审", "event_time": datetime.now() - timedelta(days=4)},
        {"case_id": CASE_IDS[7], "event_type": "filing", "title": "收到起诉书",
         "description": "收到投资者代表的集体诉讼起诉书", "event_time": datetime.now() - timedelta(days=20)},
        {"case_id": CASE_IDS[7], "event_type": "strategy", "title": "制定应诉策略",
         "description": "律师团队研讨应诉策略和抗辩方案", "event_time": datetime.now() - timedelta(days=18)},
    ]

    existing_count = (await session.execute(select(func.count()).select_from(CaseEvent))).scalar()
    if existing_count == 0:
        for e in events_data:
            session.add(CaseEvent(
                id=uid(), event_type=e["event_type"], title=e["title"],
                description=e["description"], event_time=e["event_time"],
                case_id=e["case_id"], created_by=ADMIN_ID,
            ))
        print(f"  + {len(events_data)} 条案件事件")


# ==================== 文档 ====================
async def seed_documents(session):
    from src.models.document import Document, DocumentType

    docs = [
        {"name": "XX科技合同原件.pdf", "doc_type": DocumentType.CONTRACT, "file_size": 2500000,
         "case_id": CASE_IDS[0], "mime_type": "application/pdf", "tags": ["合同", "原件"],
         "description": "软件开发合同原件扫描件"},
        {"name": "验收标准附件.docx", "doc_type": DocumentType.AGREEMENT, "file_size": 150000,
         "case_id": CASE_IDS[0], "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
         "tags": ["附件", "验收"], "description": "软件开发验收标准技术文件"},
        {"name": "劳动合同.pdf", "doc_type": DocumentType.CONTRACT, "file_size": 800000,
         "case_id": CASE_IDS[1], "mime_type": "application/pdf", "tags": ["劳动合同"],
         "description": "张某某与ZZ贸易公司签订的劳动合同"},
        {"name": "解除通知书.pdf", "doc_type": DocumentType.OTHER, "file_size": 300000,
         "case_id": CASE_IDS[1], "mime_type": "application/pdf", "tags": ["解除", "通知"],
         "description": "公司发出的劳动合同解除通知书"},
        {"name": "股权转让协议.pdf", "doc_type": DocumentType.CONTRACT, "file_size": 3200000,
         "case_id": CASE_IDS[2], "mime_type": "application/pdf", "tags": ["股权", "转让"],
         "description": "AA集团股权转让框架协议"},
        {"name": "尽调法律意见书.docx", "doc_type": DocumentType.LEGAL_OPINION, "file_size": 1800000,
         "case_id": CASE_IDS[5], "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
         "tags": ["尽调", "法律意见"], "description": "EE医药公司法律尽调意见书初稿"},
        {"name": "证据清单.xlsx", "doc_type": DocumentType.EVIDENCE, "file_size": 450000,
         "case_id": CASE_IDS[7], "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
         "tags": ["证据", "清单"], "description": "上市公司信息披露相关证据材料清单"},
        {"name": "合规审查报告模板.docx", "doc_type": DocumentType.TEMPLATE, "file_size": 520000,
         "case_id": None, "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
         "tags": ["模板", "合规"], "description": "企业年度合规审查报告标准模板"},
    ]

    from src.models.document import Document
    existing_count = (await session.execute(select(func.count()).select_from(Document))).scalar()
    if existing_count > 0:
        print(f"  文档已有 {existing_count} 条，跳过")
        return

    for d in docs:
        session.add(Document(
            id=uid(), name=d["name"], doc_type=d["doc_type"],
            file_path=f"/data/documents/{d['name']}", file_size=d["file_size"],
            mime_type=d.get("mime_type"), description=d.get("description"),
            tags=d.get("tags"), case_id=d.get("case_id"),
            org_id=ORG_ID, created_by=ADMIN_ID,
        ))
    print(f"  + {len(docs)} 条文档")


# ==================== 合同 ====================
async def seed_contracts(session):
    from src.models.contract import Contract, ContractClause, ContractRisk, ContractStatus, RiskLevel

    existing_count = (await session.execute(select(func.count()).select_from(Contract))).scalar()
    if existing_count > 0:
        print(f"  合同已有 {existing_count} 条，跳过")
        return

    contracts_data = [
        {
            "id": CONTRACT_IDS[0], "title": "软件开发服务合同", "contract_number": "HT-2026-001",
            "contract_type": "技术服务", "status": ContractStatus.ACTIVE,
            "party_a": {"name": "XX科技发展有限公司", "representative": "陈总"},
            "party_b": {"name": "YY网络科技有限公司", "representative": "刘总"},
            "amount": 5000000.0, "risk_level": RiskLevel.MEDIUM, "risk_score": 0.45,
            "sign_date": date.today() - timedelta(days=60),
            "effective_date": date.today() - timedelta(days=55),
            "expiry_date": date.today() + timedelta(days=305),
            "review_summary": "合同整体风险可控，但验收条款和违约责任条款需关注。",
        },
        {
            "id": CONTRACT_IDS[1], "title": "房屋租赁合同", "contract_number": "HT-2026-002",
            "contract_type": "租赁合同", "status": ContractStatus.SIGNED,
            "party_a": {"name": "安心法务", "representative": "管理员"},
            "party_b": {"name": "某物业管理有限公司", "representative": "王经理"},
            "amount": 360000.0, "risk_level": RiskLevel.LOW, "risk_score": 0.15,
            "sign_date": date.today() - timedelta(days=30),
            "effective_date": date.today() - timedelta(days=25),
            "expiry_date": date.today() + timedelta(days=340),
            "review_summary": "标准租赁合同，条款完备，风险低。",
        },
        {
            "id": CONTRACT_IDS[2], "title": "股权转让协议", "contract_number": "HT-2026-003",
            "contract_type": "投资并购", "status": ContractStatus.UNDER_REVIEW,
            "party_a": {"name": "AA投资集团", "representative": "张总"},
            "party_b": {"name": "李某某", "representative": "李某某"},
            "amount": 20000000.0, "risk_level": RiskLevel.HIGH, "risk_score": 0.78,
            "sign_date": None, "effective_date": None,
            "expiry_date": None,
            "review_summary": "高风险合同，对赌条款、竞业限制、资产披露义务等需重点审查。",
        },
        {
            "id": CONTRACT_IDS[3], "title": "保密协议(NDA)", "contract_number": "HT-2026-004",
            "contract_type": "保密协议", "status": ContractStatus.ACTIVE,
            "party_a": {"name": "某上市集团", "representative": "法务总监"},
            "party_b": {"name": "EE医药科技有限公司", "representative": "CEO"},
            "amount": 0.0, "risk_level": RiskLevel.LOW, "risk_score": 0.10,
            "sign_date": date.today() - timedelta(days=20),
            "effective_date": date.today() - timedelta(days=20),
            "expiry_date": date.today() + timedelta(days=710),
            "review_summary": "标准NDA，保密范围和期限合理。",
        },
        {
            "id": CONTRACT_IDS[4], "title": "原材料采购合同", "contract_number": "HT-2026-005",
            "contract_type": "买卖合同", "status": ContractStatus.PENDING_REVIEW,
            "party_a": {"name": "FF制造有限公司", "representative": "采购总监"},
            "party_b": {"name": "GG材料科技有限公司", "representative": "销售经理"},
            "amount": 1200000.0, "risk_level": RiskLevel.MEDIUM, "risk_score": 0.50,
            "sign_date": None, "effective_date": None,
            "expiry_date": None,
            "review_summary": "质量保证条款和违约赔偿条款需进一步完善。",
        },
        {
            "id": CONTRACT_IDS[5], "title": "法律顾问服务协议", "contract_number": "HT-2026-006",
            "contract_type": "服务合同", "status": ContractStatus.ACTIVE,
            "party_a": {"name": "DD地产开发有限公司", "representative": "总裁"},
            "party_b": {"name": "安心法务", "representative": "管理员"},
            "amount": 500000.0, "risk_level": RiskLevel.LOW, "risk_score": 0.12,
            "sign_date": date.today() - timedelta(days=90),
            "effective_date": date.today() - timedelta(days=85),
            "expiry_date": date.today() + timedelta(days=275),
            "review_summary": "我方为乙方，服务范围和费用条款清晰明确。",
        },
    ]

    for c in contracts_data:
        session.add(Contract(
            id=c["id"], title=c["title"], contract_number=c["contract_number"],
            contract_type=c["contract_type"], status=c["status"],
            party_a=c["party_a"], party_b=c["party_b"],
            amount=c["amount"], risk_level=c.get("risk_level"),
            risk_score=c.get("risk_score"),
            sign_date=c.get("sign_date"), effective_date=c.get("effective_date"),
            expiry_date=c.get("expiry_date"),
            review_summary=c.get("review_summary"),
            org_id=ORG_ID, reviewed_by=ADMIN_ID,
        ))
    print(f"  + {len(contracts_data)} 份合同")

    await session.flush()

    # 合同条款
    clauses_data = [
        # 软件开发合同
        {"contract_id": CONTRACT_IDS[0], "clause_number": "3.1", "clause_type": "交付",
         "title": "软件交付条款", "content": "乙方应在合同签订后180日内完成软件开发并交付甲方验收。",
         "risk_level": RiskLevel.MEDIUM, "is_standard": True},
        {"contract_id": CONTRACT_IDS[0], "clause_number": "5.2", "clause_type": "违约",
         "title": "逾期交付违约金", "content": "乙方逾期交付的，每逾期一日，应向甲方支付合同总价0.5%的违约金。",
         "risk_level": RiskLevel.HIGH, "is_standard": False,
         "suggestions": ["建议将违约金比例降至0.1%/日", "建议设置违约金上限为合同总价的20%"]},
        # 股权转让协议
        {"contract_id": CONTRACT_IDS[2], "clause_number": "4.1", "clause_type": "对赌",
         "title": "业绩对赌条款", "content": "目标公司未来三年净利润不低于3000万/年，否则转让方应按差额部分进行现金补偿。",
         "risk_level": RiskLevel.HIGH, "is_standard": False,
         "suggestions": ["建议增加业绩承诺的合理性论证", "建议约定对赌触发的具体计算方式"]},
        {"contract_id": CONTRACT_IDS[2], "clause_number": "6.1", "clause_type": "竞业限制",
         "title": "竞业限制条款", "content": "转让方在股权转让完成后5年内不得从事与目标公司同类业务。",
         "risk_level": RiskLevel.MEDIUM, "is_standard": True},
        {"contract_id": CONTRACT_IDS[2], "clause_number": "7.3", "clause_type": "陈述保证",
         "title": "资产完整性保证", "content": "转让方保证目标公司资产负债表真实完整，不存在未披露的或有负债。",
         "risk_level": RiskLevel.CRITICAL, "is_standard": True},
        # 采购合同
        {"contract_id": CONTRACT_IDS[4], "clause_number": "2.1", "clause_type": "质量",
         "title": "质量标准", "content": "乙方提供的原材料应符合国家标准GB/T XXXXX-2024。",
         "risk_level": RiskLevel.MEDIUM, "is_standard": True},
        {"contract_id": CONTRACT_IDS[4], "clause_number": "4.2", "clause_type": "退换货",
         "title": "质量不合格退换货", "content": "甲方发现质量不合格的，有权在10日内退换货，运费由乙方承担。",
         "risk_level": RiskLevel.LOW, "is_standard": True},
    ]

    for cl in clauses_data:
        session.add(ContractClause(
            id=uid(), clause_number=cl["clause_number"], clause_type=cl["clause_type"],
            title=cl.get("title"), content=cl["content"],
            risk_level=cl.get("risk_level"), is_standard=cl.get("is_standard", True),
            suggestions=cl.get("suggestions"),
            contract_id=cl["contract_id"],
        ))
    print(f"  + {len(clauses_data)} 条合同条款")

    # 合同风险
    risks_data = [
        {"contract_id": CONTRACT_IDS[0], "risk_type": "违约金过高", "risk_level": RiskLevel.HIGH,
         "title": "逾期交付违约金比例过高", "description": "0.5%/日的违约金比例远超行业惯例（通常0.05%-0.1%/日），且无上限约定。",
         "related_clause": "5.2", "suggestion": "建议将违约金比例调整为0.05%/日，并设置总额上限为合同价的15%。"},
        {"contract_id": CONTRACT_IDS[0], "risk_type": "验收标准不明", "risk_level": RiskLevel.MEDIUM,
         "title": "验收标准约定模糊", "description": "合同未明确软件功能验收的具体标准和测试流程。",
         "related_clause": "3.1", "suggestion": "建议补充详细的功能验收标准、测试用例及验收流程时间表。"},
        {"contract_id": CONTRACT_IDS[2], "risk_type": "对赌风险", "risk_level": RiskLevel.CRITICAL,
         "title": "业绩对赌条款风险极高", "description": "3000万/年的业绩承诺缺乏合理性论证，且补偿计算方式不够明确。",
         "related_clause": "4.1", "suggestion": "建议聘请独立审计机构对业绩承诺进行可行性评估。"},
        {"contract_id": CONTRACT_IDS[2], "risk_type": "资产隐瞒", "risk_level": RiskLevel.HIGH,
         "title": "目标公司可能存在未披露负债", "description": "尽调中发现目标公司存在多笔未入账的关联交易和担保。",
         "related_clause": "7.3", "suggestion": "建议要求转让方提供所有关联交易明细并安排独立审计。"},
        {"contract_id": CONTRACT_IDS[4], "risk_type": "质量标准引用", "risk_level": RiskLevel.MEDIUM,
         "title": "质量标准引用不完整", "description": "仅引用了国标号，未明确具体的技术指标和检测方法。",
         "related_clause": "2.1", "suggestion": "建议补充具体的技术参数要求和第三方检测机构约定。"},
    ]

    for r in risks_data:
        session.add(ContractRisk(
            id=uid(), risk_type=r["risk_type"], risk_level=r["risk_level"],
            title=r["title"], description=r["description"],
            related_clause=r.get("related_clause"), suggestion=r.get("suggestion"),
            contract_id=r["contract_id"],
        ))
    print(f"  + {len(risks_data)} 条合同风险")


# ==================== 任务 ====================
async def seed_tasks(session):
    from src.models.task import Task

    existing_count = (await session.execute(select(func.count()).select_from(Task))).scalar()
    if existing_count > 0:
        print(f"  任务已有 {existing_count} 条，跳过")
        return

    tasks_data = [
        {"title": "准备XX科技案件庭审材料", "description": "整理证据清单、准备代理词和答辩状",
         "status": "in_progress", "priority": "high", "due_date": date.today() + timedelta(days=3),
         "tags": ["庭审", "合同纠纷"], "assignee_id": USER_IDS["lawyer1"], "case_id": CASE_IDS[0]},
        {"title": "审查股权转让协议修订稿", "description": "对方发来的协议修订稿，需逐条审查",
         "status": "todo", "priority": "high", "due_date": date.today() + timedelta(days=5),
         "tags": ["审查", "股权"], "assignee_id": USER_IDS["lawyer1"], "case_id": CASE_IDS[2]},
        {"title": "完成EE医药尽调报告终稿", "description": "将初稿修改意见汇总，形成终稿报告",
         "status": "in_progress", "priority": "high", "due_date": date.today() + timedelta(days=7),
         "tags": ["尽调", "报告"], "assignee_id": USER_IDS["lawyer2"], "case_id": CASE_IDS[5]},
        {"title": "张某劳动仲裁材料送达", "description": "将仲裁申请材料送达至劳动仲裁委员会",
         "status": "done", "priority": "medium", "due_date": date.today() - timedelta(days=1),
         "tags": ["劳动仲裁", "送达"], "assignee_id": USER_IDS["paralegal1"], "case_id": CASE_IDS[1]},
        {"title": "DD地产合规检查报告撰写", "description": "完成环保合规部分的检查报告",
         "status": "in_progress", "priority": "medium", "due_date": date.today() + timedelta(days=10),
         "tags": ["合规", "报告"], "assignee_id": USER_IDS["lawyer2"], "case_id": CASE_IDS[4]},
        {"title": "更新客户合同管理台账", "description": "将本月新增合同录入管理系统",
         "status": "todo", "priority": "low", "due_date": date.today() + timedelta(days=14),
         "tags": ["台账", "管理"], "assignee_id": USER_IDS["paralegal2"], "case_id": None},
        {"title": "上市公司集体诉讼应诉策略会", "description": "与律师团队讨论应诉策略，准备会议纪要",
         "status": "todo", "priority": "high", "due_date": date.today() + timedelta(days=2),
         "tags": ["诉讼", "策略"], "assignee_id": USER_IDS["lawyer1"], "case_id": CASE_IDS[7]},
        {"title": "知识库法律法规更新", "description": "将最新发布的司法解释和部门规章入库",
         "status": "done", "priority": "low", "due_date": date.today() - timedelta(days=3),
         "tags": ["知识库", "更新"], "assignee_id": USER_IDS["paralegal1"], "case_id": None},
    ]

    for t in tasks_data:
        session.add(Task(
            id=uid(), title=t["title"], description=t["description"],
            status=t["status"], priority=t["priority"], due_date=t.get("due_date"),
            tags=t.get("tags", []), assignee_id=t.get("assignee_id"),
            case_id=t.get("case_id"), created_by=ADMIN_ID, org_id=ORG_ID,
        ))
    print(f"  + {len(tasks_data)} 条任务")


# ==================== 案源线索 ====================
async def seed_leads(session):
    from src.models.lead import Lead

    existing_count = (await session.execute(select(func.count()).select_from(Lead))).scalar()
    if existing_count > 0:
        print(f"  案源已有 {existing_count} 条，跳过")
        return

    leads_data = [
        {"client_name": "深圳创新科技有限公司", "contact_info": "138xxxx5678", "source": "转介绍",
         "case_type": "合同审查", "estimated_amount": 80000.0, "stage": "qualified",
         "assignee_id": USER_IDS["lawyer1"],
         "follow_ups": [
             {"id": "1", "date": (date.today() - timedelta(days=10)).isoformat(), "note": "初次电话沟通，了解需求", "type": "phone"},
             {"id": "2", "date": (date.today() - timedelta(days=5)).isoformat(), "note": "面谈，确认合同审查范围", "type": "meeting"},
         ]},
        {"client_name": "北京文化传媒集团", "contact_info": "131xxxx9012", "source": "线上咨询",
         "case_type": "知识产权", "estimated_amount": 200000.0, "stage": "proposal",
         "assignee_id": USER_IDS["lawyer3"],
         "follow_ups": [
             {"id": "1", "date": (date.today() - timedelta(days=15)).isoformat(), "note": "收到在线咨询表单", "type": "online"},
             {"id": "2", "date": (date.today() - timedelta(days=12)).isoformat(), "note": "电话回访确认需求", "type": "phone"},
             {"id": "3", "date": (date.today() - timedelta(days=3)).isoformat(), "note": "发送服务方案和报价", "type": "email"},
         ]},
        {"client_name": "杭州智能制造有限公司", "contact_info": "150xxxx3456", "source": "主动拓展",
         "case_type": "劳动纠纷", "estimated_amount": 50000.0, "stage": "contacted",
         "assignee_id": USER_IDS["lawyer2"],
         "follow_ups": [
             {"id": "1", "date": (date.today() - timedelta(days=3)).isoformat(), "note": "拜访客户，了解劳动纠纷情况", "type": "meeting"},
         ]},
        {"client_name": "上海金融投资管理公司", "contact_info": "139xxxx7890", "source": "转介绍",
         "case_type": "投资并购", "estimated_amount": 500000.0, "stage": "new",
         "assignee_id": None, "follow_ups": []},
        {"client_name": "广州医药科技有限公司", "contact_info": "135xxxx2345", "source": "电话咨询",
         "case_type": "合规咨询", "estimated_amount": 120000.0, "stage": "contacted",
         "assignee_id": USER_IDS["lawyer2"],
         "follow_ups": [
             {"id": "1", "date": (date.today() - timedelta(days=7)).isoformat(), "note": "来电咨询医药行业合规问题", "type": "phone"},
         ]},
        {"client_name": "成都互联网公司", "contact_info": "186xxxx6789", "source": "线上咨询",
         "case_type": "数据合规", "estimated_amount": 150000.0, "stage": "won",
         "assignee_id": USER_IDS["lawyer1"],
         "follow_ups": [
             {"id": "1", "date": (date.today() - timedelta(days=30)).isoformat(), "note": "初步沟通", "type": "phone"},
             {"id": "2", "date": (date.today() - timedelta(days=20)).isoformat(), "note": "提交方案", "type": "email"},
             {"id": "3", "date": (date.today() - timedelta(days=10)).isoformat(), "note": "签约成功", "type": "meeting"},
         ]},
        {"client_name": "武汉建设工程集团", "contact_info": "133xxxx0123", "source": "主动拓展",
         "case_type": "工程合同", "estimated_amount": 300000.0, "stage": "qualified",
         "assignee_id": USER_IDS["lawyer3"],
         "follow_ups": [
             {"id": "1", "date": (date.today() - timedelta(days=8)).isoformat(), "note": "通过行业协会获取联系方式", "type": "other"},
             {"id": "2", "date": (date.today() - timedelta(days=4)).isoformat(), "note": "电话沟通，确认有法律服务需求", "type": "phone"},
         ]},
        {"client_name": "南京教育科技公司", "contact_info": "152xxxx4567", "source": "电话咨询",
         "case_type": "股权结构", "estimated_amount": 100000.0, "stage": "lost",
         "assignee_id": USER_IDS["lawyer2"],
         "follow_ups": [
             {"id": "1", "date": (date.today() - timedelta(days=25)).isoformat(), "note": "来电咨询股权架构设计", "type": "phone"},
             {"id": "2", "date": (date.today() - timedelta(days=20)).isoformat(), "note": "发送方案，客户认为费用偏高", "type": "email"},
             {"id": "3", "date": (date.today() - timedelta(days=15)).isoformat(), "note": "客户选择了其他律所", "type": "phone"},
         ]},
    ]

    for l in leads_data:
        session.add(Lead(
            id=uid(), client_name=l["client_name"], contact_info=l.get("contact_info"),
            source=l.get("source"), case_type=l.get("case_type"),
            estimated_amount=l.get("estimated_amount", 0.0), stage=l["stage"],
            follow_ups=l.get("follow_ups", []),
            assignee_id=l.get("assignee_id"), created_by=ADMIN_ID, org_id=ORG_ID,
        ))
    print(f"  + {len(leads_data)} 条案源线索")


# ==================== 专家 ====================
async def seed_experts(session):
    from src.models.expert import Expert

    existing_count = (await session.execute(select(func.count()).select_from(Expert))).scalar()
    if existing_count > 0:
        print(f"  专家已有 {existing_count} 条，跳过")
        return

    experts_data = [
        {"name": "张伟", "title": "高级合伙人", "specialty": ["合同法", "公司法", "并购重组"],
         "years_of_experience": 18, "rating": 4.9, "cases_handled": 356,
         "description": "专注于公司法与并购重组领域18年，成功处理多起大型并购交易和上市公司法律事务。",
         "achievements": ["中国十佳商事律师", "全国优秀律师", "2023年最佳并购交易奖"],
         "user_id": USER_IDS["lawyer1"]},
        {"name": "李娜", "title": "合伙人", "specialty": ["劳动法", "合规", "数据保护"],
         "years_of_experience": 12, "rating": 4.8, "cases_handled": 245,
         "description": "劳动法与合规领域专家，为众多跨国企业提供劳动合规和数据保护法律服务。",
         "achievements": ["优秀劳动法律师", "2024年最佳合规律师提名"],
         "user_id": USER_IDS["lawyer2"]},
        {"name": "王强", "title": "合伙人", "specialty": ["知识产权", "商标", "著作权"],
         "years_of_experience": 15, "rating": 4.7, "cases_handled": 198,
         "description": "知识产权领域资深律师，擅长商标、著作权、专利等知识产权纠纷的诉讼与非诉业务。",
         "achievements": ["知名知产律师", "IP年度最佳代理案例"],
         "user_id": USER_IDS["lawyer3"]},
        {"name": "刘芳", "title": "资深律师", "specialty": ["房地产", "建筑工程", "PPP"],
         "years_of_experience": 10, "rating": 4.6, "cases_handled": 167,
         "description": "专注于房地产和建筑工程领域，在PPP项目和政府采购方面有丰富经验。",
         "achievements": ["优秀房地产律师"],
         "user_id": None},
        {"name": "陈明", "title": "资深律师", "specialty": ["刑事辩护", "行政法", "环境法"],
         "years_of_experience": 20, "rating": 4.9, "cases_handled": 420,
         "description": "二十年刑事辩护经验，多次成功办理重大刑事案件，在行政诉讼领域也有突出成绩。",
         "achievements": ["全国知名刑辩律师", "十大经典辩护案例", "法律援助先进个人"],
         "user_id": None},
        {"name": "赵雪", "title": "高级合伙人", "specialty": ["金融", "证券", "基金"],
         "years_of_experience": 16, "rating": 4.8, "cases_handled": 280,
         "description": "金融证券领域专家，曾主导多家企业IPO法律服务及私募基金设立。",
         "achievements": ["最佳资本市场律师", "百亿基金首席法律顾问"],
         "user_id": None},
    ]

    for e in experts_data:
        session.add(Expert(
            id=uid(), name=e["name"], title=e.get("title"),
            specialty=e.get("specialty", []),
            years_of_experience=e.get("years_of_experience", 0),
            rating=e.get("rating", 0.0), cases_handled=e.get("cases_handled", 0),
            description=e.get("description"), achievements=e.get("achievements", []),
            user_id=e.get("user_id"), org_id=ORG_ID,
        ))
    print(f"  + {len(experts_data)} 位专家")


# ==================== 课程 ====================
async def seed_courses(session):
    from src.models.course import Course, CourseProgress

    existing_count = (await session.execute(select(func.count()).select_from(Course))).scalar()
    if existing_count > 0:
        print(f"  课程已有 {existing_count} 条，跳过")
        return

    courses_data = [
        {"id": COURSE_IDS[0], "title": "民法典合同编精讲", "instructor": "张伟",
         "category": "regulation", "duration": "24学时", "lessons": 24,
         "description": "系统讲解民法典合同编的重要条文，结合实务案例深入分析。",
         "level": "进阶", "tags": ["民法典", "合同法"]},
        {"id": COURSE_IDS[1], "title": "劳动法实务操作指南", "instructor": "李娜",
         "category": "practice", "duration": "18学时", "lessons": 18,
         "description": "从招聘入职到离职解除，全流程劳动法实务操作及风险防范。",
         "level": "入门", "tags": ["劳动法", "实务"]},
        {"id": COURSE_IDS[2], "title": "公司并购重组法律实务", "instructor": "张伟",
         "category": "case_study", "duration": "32学时", "lessons": 32,
         "description": "通过经典并购案例，深入讲解股权收购、资产收购、合并分立等法律实务。",
         "level": "高级", "tags": ["并购", "公司法", "案例"]},
        {"id": COURSE_IDS[3], "title": "知识产权侵权诉讼实战", "instructor": "王强",
         "category": "case_study", "duration": "20学时", "lessons": 20,
         "description": "商标、著作权、专利侵权诉讼的实战经验分享和策略分析。",
         "level": "进阶", "tags": ["知识产权", "诉讼"]},
        {"id": COURSE_IDS[4], "title": "企业数据合规与个人信息保护", "instructor": "李娜",
         "category": "regulation", "duration": "16学时", "lessons": 16,
         "description": "解读《个人信息保护法》《数据安全法》，指导企业建立合规体系。",
         "level": "入门", "tags": ["数据合规", "个保法"]},
        {"id": COURSE_IDS[5], "title": "法律人必备的AI工具应用", "instructor": "系统管理员",
         "category": "practice", "duration": "12学时", "lessons": 12,
         "description": "如何利用AI工具提升法律工作效率，包括合同审查、法律研究、文书起草等。",
         "level": "入门", "tags": ["AI", "工具", "效率"]},
        {"id": COURSE_IDS[6], "title": "律师执业资格考试冲刺班", "instructor": "陈明",
         "category": "exam", "duration": "48学时", "lessons": 48,
         "description": "针对律师执业资格考试的重点难点进行系统梳理和模拟训练。",
         "level": "入门", "tags": ["考试", "律师资格"]},
        {"id": COURSE_IDS[7], "title": "金融监管与合规风控", "instructor": "赵雪",
         "category": "regulation", "duration": "28学时", "lessons": 28,
         "description": "深入解析金融监管政策和合规风控体系建设，适合金融机构法务人员。",
         "level": "高级", "tags": ["金融", "监管", "风控"]},
    ]

    for c in courses_data:
        session.add(Course(
            id=c["id"], title=c["title"], instructor=c.get("instructor"),
            category=c["category"], duration=c.get("duration"),
            lessons=c.get("lessons", 0), description=c.get("description"),
            level=c.get("level", "入门"), tags=c.get("tags", []),
            org_id=ORG_ID, created_by=ADMIN_ID,
        ))
    print(f"  + {len(courses_data)} 门课程")

    await session.flush()

    # 学习进度
    progress_data = [
        {"user_id": ADMIN_ID, "course_id": COURSE_IDS[0], "progress": 75, "completed_lessons": list(range(1, 19))},
        {"user_id": ADMIN_ID, "course_id": COURSE_IDS[1], "progress": 100, "completed_lessons": list(range(1, 19))},
        {"user_id": ADMIN_ID, "course_id": COURSE_IDS[4], "progress": 30, "completed_lessons": [1, 2, 3, 4, 5]},
        {"user_id": ADMIN_ID, "course_id": COURSE_IDS[5], "progress": 50, "completed_lessons": [1, 2, 3, 4, 5, 6]},
        {"user_id": USER_IDS["lawyer1"], "course_id": COURSE_IDS[2], "progress": 60, "completed_lessons": list(range(1, 20))},
    ]

    for p in progress_data:
        session.add(CourseProgress(
            id=uid(), user_id=p["user_id"], course_id=p["course_id"],
            progress=p["progress"], completed_lessons=p["completed_lessons"],
        ))
    print(f"  + {len(progress_data)} 条学习进度")


# ==================== 通知 ====================
async def seed_notifications(session):
    from src.models.notification import Notification

    existing_count = (await session.execute(select(func.count()).select_from(Notification))).scalar()
    if existing_count > 0:
        print(f"  通知已有 {existing_count} 条，跳过")
        return

    notifications_data = [
        {"type": "urgent", "title": "庭审提醒", "message": "XX科技公司合同纠纷案将于3天后开庭，请确认庭审材料准备情况。",
         "related_link": "/cases", "is_read": False},
        {"type": "warning", "title": "合同到期预警", "message": "法律顾问服务协议(HT-2026-006)将于275天后到期，请提前准备续签事宜。",
         "related_link": "/contracts", "is_read": False},
        {"type": "info", "title": "新案源分配", "message": "上海金融投资管理公司的投资并购咨询案源已分配给您，请及时跟进。",
         "related_link": "/leads", "is_read": False},
        {"type": "success", "title": "尽调报告审批通过", "message": "EE医药公司法律尽调报告初稿已通过内部审核，可提交客户。",
         "related_link": "/cases", "is_read": True},
        {"type": "urgent", "title": "舆情预警", "message": "监控到与HH上市公司相关的负面舆情3条，风险等级：高。",
         "related_link": "/news", "is_read": False},
        {"type": "info", "title": "知识库更新", "message": "最新《公司法》司法解释已入库，共12篇法条，可在知识库中查阅。",
         "related_link": "/knowledge", "is_read": True},
        {"type": "warning", "title": "任务逾期提醒", "message": "您有2项任务即将逾期，请及时处理。",
         "related_link": "/tasks", "is_read": False},
        {"type": "success", "title": "案源签约成功", "message": "成都互联网公司数据合规项目已签约成功，合同金额15万元。",
         "related_link": "/leads", "is_read": True},
    ]

    for n in notifications_data:
        session.add(Notification(
            id=uid(), user_id=ADMIN_ID,
            type=n["type"], title=n["title"], message=n["message"],
            is_read=n.get("is_read", False),
            related_link=n.get("related_link"),
        ))
    print(f"  + {len(notifications_data)} 条通知")


# ==================== 知识库 ====================
async def seed_knowledge(session):
    from src.models.knowledge import KnowledgeBase as KB, KnowledgeDocument, KnowledgeType

    existing_count = (await session.execute(select(func.count()).select_from(KB))).scalar()
    if existing_count > 0:
        print(f"  知识库已有 {existing_count} 条，跳过")
        return

    kbs = [
        {"id": KB_IDS[0], "name": "法律法规库", "description": "收录全国人大及常委会发布的现行有效法律法规",
         "knowledge_type": KnowledgeType.LAW, "doc_count": 3, "is_public": True},
        {"id": KB_IDS[1], "name": "司法判例库", "description": "最高人民法院及各级法院公布的典型案例",
         "knowledge_type": KnowledgeType.CASE, "doc_count": 3, "is_public": True},
        {"id": KB_IDS[2], "name": "合同模板库", "description": "各类标准合同模板，覆盖常见商事合同类型",
         "knowledge_type": KnowledgeType.TEMPLATE, "doc_count": 3, "is_public": False},
        {"id": KB_IDS[3], "name": "内部知识库", "description": "事务所内部知识沉淀，包括案例分析、操作指南等",
         "knowledge_type": KnowledgeType.INTERNAL, "doc_count": 3, "is_public": False},
    ]

    for kb in kbs:
        session.add(KB(
            id=kb["id"], name=kb["name"], description=kb["description"],
            knowledge_type=kb["knowledge_type"], doc_count=kb["doc_count"],
            is_public=kb["is_public"], org_id=ORG_ID, created_by=ADMIN_ID,
        ))
    print(f"  + {len(kbs)} 个知识库")

    await session.flush()

    # 知识库文档
    docs = [
        # 法律法规库
        {"kb_id": KB_IDS[0], "title": "中华人民共和国民法典", "source": "全国人大", "law_category": "民事法律",
         "effective_date": "2021-01-01", "issuing_authority": "全国人民代表大会",
         "content": "《中华人民共和国民法典》是新中国成立以来第一部以法典命名的法律，共7编、1260条。涵盖总则、物权、合同、人格权、婚姻家庭、继承、侵权责任等内容。",
         "summary": "我国民事领域的基本法律，调整平等主体的人身关系和财产关系。", "tags": ["民法典", "基本法律"], "is_processed": True},
        {"kb_id": KB_IDS[0], "title": "中华人民共和国公司法（2023修订）", "source": "全国人大常委会", "law_category": "商事法律",
         "effective_date": "2024-07-01", "issuing_authority": "全国人民代表大会常务委员会",
         "content": "修订后的公司法对公司的设立、组织机构、股东权利义务、公司合并分立、解散清算等进行了全面规定，新增了审计委员会制度和类别股制度。",
         "summary": "规范公司组织和行为的基本商事法律。", "tags": ["公司法", "商法"], "is_processed": True},
        {"kb_id": KB_IDS[0], "title": "中华人民共和国个人信息保护法", "source": "全国人大常委会", "law_category": "信息安全",
         "effective_date": "2021-11-01", "issuing_authority": "全国人民代表大会常务委员会",
         "content": "个保法明确了个人信息处理规则、个人信息跨境提供规则、个人信息处理者的义务等，规定了最高营业额5%的罚款。",
         "summary": "我国个人信息保护领域的专门法律。", "tags": ["个保法", "数据安全"], "is_processed": True},
        # 司法判例库
        {"kb_id": KB_IDS[1], "title": "最高法指导案例：某科技公司股东知情权纠纷", "source": "最高人民法院",
         "content": "案情摘要：原告系被告公司股东，持股15%。原告请求查阅公司会计账簿，被告以涉及商业秘密为由拒绝。法院认为股东有权查阅会计账簿，公司应当提供。",
         "summary": "股东知情权的行使范围和限制条件。", "tags": ["股东权利", "知情权"], "is_processed": True,
         "law_category": "公司法"},
        {"kb_id": KB_IDS[1], "title": "劳动争议典型案例：经济性裁员程序违法", "source": "最高人民法院",
         "content": "用人单位以经营困难为由裁员，但未按《劳动合同法》第41条规定提前30日向工会说明情况并向劳动行政部门报告。法院认定裁员违法，判决支付赔偿金。",
         "summary": "经济性裁员的法定程序要求和违法后果。", "tags": ["劳动法", "裁员"], "is_processed": True,
         "law_category": "劳动法"},
        {"kb_id": KB_IDS[1], "title": "知识产权典型案例：网络著作权侵权认定", "source": "北京互联网法院",
         "content": "被告在其运营的平台上传播原告享有著作权的视频内容，未经许可且未支付报酬。法院适用《著作权法》第10条和第48条，判决被告赔偿经济损失及合理开支。",
         "summary": "网络环境下著作权侵权的认定标准和赔偿计算。", "tags": ["著作权", "网络侵权"], "is_processed": True,
         "law_category": "知识产权"},
        # 合同模板库
        {"kb_id": KB_IDS[2], "title": "技术开发合同范本", "source": "内部模板",
         "content": "甲方委托乙方进行技术开发，双方就开发内容、技术标准、交付验收、知识产权归属、保密义务、违约责任等条款达成如下协议...",
         "summary": "适用于软件开发、系统集成等技术开发项目的合同模板。", "tags": ["合同模板", "技术开发"], "is_processed": True},
        {"kb_id": KB_IDS[2], "title": "保密协议(NDA)范本", "source": "内部模板",
         "content": "鉴于双方拟就___项目进行合作/谈判，为保护双方商业秘密和机密信息，双方约定如下保密义务...",
         "summary": "通用保密协议模板，适用于商务合作前的信息保护。", "tags": ["合同模板", "保密协议"], "is_processed": True},
        {"kb_id": KB_IDS[2], "title": "股权转让协议范本", "source": "内部模板",
         "content": "转让方将其持有的目标公司____%股权转让给受让方，双方就转让价格、支付方式、交割条件、陈述保证、违约责任等条款约定如下...",
         "summary": "有限责任公司股权转让协议标准模板。", "tags": ["合同模板", "股权转让"], "is_processed": True},
        # 内部知识库
        {"kb_id": KB_IDS[3], "title": "合同审查操作指南", "source": "内部知识",
         "content": "一、合同审查基本流程：1.形式审查（主体资格、签章、授权）2.实质审查（权利义务、风险条款、违约责任）3.出具审查意见...",
         "summary": "事务所合同审查的标准操作流程和注意事项。", "tags": ["操作指南", "合同审查"], "is_processed": True},
        {"kb_id": KB_IDS[3], "title": "劳动争议处理经验汇编", "source": "内部知识",
         "content": "本汇编收录了近年来事务所处理的典型劳动争议案例经验，包括违法解除、竞业限制、工伤认定等常见争议类型的处理策略和注意事项。",
         "summary": "劳动争议典型案例的处理经验总结。", "tags": ["经验汇编", "劳动法"], "is_processed": True},
        {"kb_id": KB_IDS[3], "title": "尽职调查工作手册", "source": "内部知识",
         "content": "一、尽调准备：确定尽调范围、组建尽调团队、制定工作计划。二、尽调实施：资料审查、现场访谈、数据分析。三、尽调报告：发现问题清单、风险评估、建议措施。",
         "summary": "法律尽职调查的完整工作流程和方法论。", "tags": ["操作指南", "尽职调查"], "is_processed": True},
    ]

    for d in docs:
        session.add(KnowledgeDocument(
            id=uid(), title=d["title"], source=d.get("source"),
            content=d["content"], summary=d.get("summary"),
            tags=d.get("tags", []), law_category=d.get("law_category"),
            effective_date=d.get("effective_date"),
            issuing_authority=d.get("issuing_authority"),
            is_processed=d.get("is_processed", False),
            knowledge_base_id=d["kb_id"],
        ))
    print(f"  + {len(docs)} 篇知识文档")


# ==================== 舆情 ====================
async def seed_sentiment(session):
    from src.models.sentiment import SentimentMonitor, SentimentRecord, SentimentAlert
    from src.models.sentiment import SentimentType, SourceType
    from src.models.sentiment import RiskLevel as SRiskLevel, AlertType, AlertLevel

    existing_count = (await session.execute(select(func.count()).select_from(SentimentMonitor))).scalar()
    if existing_count > 0:
        print(f"  舆情已有数据，跳过")
        return

    # 监控配置
    monitors = [
        {"id": MONITOR_IDS[0], "name": "客户企业舆情监控",
         "description": "监控所有客户企业的公开舆情信息",
         "keywords": ["XX科技", "AA投资集团", "HH上市公司", "DD地产", "EE医药"],
         "sources": ["news", "social_media", "forum", "official"],
         "total_records": 6, "negative_count": 2, "alert_count": 1},
        {"id": MONITOR_IDS[1], "name": "法律行业动态监控",
         "description": "监控法律法规变动和行业政策动态",
         "keywords": ["法律法规", "司法解释", "律师行业", "法治"],
         "sources": ["news", "official"],
         "total_records": 4, "negative_count": 0, "alert_count": 0},
    ]

    for m in monitors:
        session.add(SentimentMonitor(
            id=m["id"], name=m["name"], description=m["description"],
            keywords=m["keywords"], sources=m.get("sources"),
            total_records=m.get("total_records", 0),
            negative_count=m.get("negative_count", 0),
            alert_count=m.get("alert_count", 0),
            org_id=ORG_ID, created_by=ADMIN_ID,
        ))
    print(f"  + {len(monitors)} 个舆情监控")

    await session.flush()

    # 舆情记录
    records_data = [
        {"title": "XX科技公司获得新一轮融资", "content": "XX科技发展有限公司宣布完成B轮融资，融资额达1亿元，将用于核心技术研发。",
         "keyword": "XX科技", "source": "创投日报", "source_type": SourceType.NEWS,
         "sentiment_type": SentimentType.POSITIVE, "sentiment_score": 0.85,
         "risk_level": SRiskLevel.LOW, "risk_score": 0.1, "author": "记者张三",
         "publish_time": datetime.now() - timedelta(days=2), "monitor_id": MONITOR_IDS[0],
         "summary": "正面消息，客户公司融资成功，业务发展良好。"},
        {"title": "HH上市公司被立案调查", "content": "证监会因HH上市公司涉嫌信息披露违规，决定对其立案调查。受此影响，公司股价跌停。",
         "keyword": "HH上市公司", "source": "财经新闻网", "source_type": SourceType.NEWS,
         "sentiment_type": SentimentType.NEGATIVE, "sentiment_score": -0.92,
         "risk_level": SRiskLevel.CRITICAL, "risk_score": 0.95, "author": "财经编辑部",
         "publish_time": datetime.now() - timedelta(days=1), "monitor_id": MONITOR_IDS[0],
         "summary": "重大负面舆情，客户公司被证监会立案调查，需紧急应对。"},
        {"title": "AA投资集团荣获行业大奖", "content": "AA投资集团在年度投资峰会上荣获'最佳投资机构'称号。",
         "keyword": "AA投资集团", "source": "投资界", "source_type": SourceType.NEWS,
         "sentiment_type": SentimentType.POSITIVE, "sentiment_score": 0.70,
         "risk_level": SRiskLevel.LOW, "risk_score": 0.05, "author": "投资界记者",
         "publish_time": datetime.now() - timedelta(days=5), "monitor_id": MONITOR_IDS[0],
         "summary": "正面报道，客户企业品牌影响力提升。"},
        {"title": "DD地产项目被业主集体投诉", "content": "DD地产开发的某住宅项目因房屋质量问题被业主在社交媒体集体投诉，引发广泛关注。",
         "keyword": "DD地产", "source": "微博热搜", "source_type": SourceType.SOCIAL_MEDIA,
         "sentiment_type": SentimentType.NEGATIVE, "sentiment_score": -0.78,
         "risk_level": SRiskLevel.HIGH, "risk_score": 0.80, "author": "业主代表",
         "publish_time": datetime.now() - timedelta(days=3), "monitor_id": MONITOR_IDS[0],
         "summary": "负面舆情，客户地产项目遭业主投诉，可能引发诉讼风险。"},
        {"title": "EE医药新药获批上市", "content": "EE医药科技有限公司自主研发的某创新药物获国家药监局批准上市，填补国内空白。",
         "keyword": "EE医药", "source": "医药经济报", "source_type": SourceType.NEWS,
         "sentiment_type": SentimentType.POSITIVE, "sentiment_score": 0.90,
         "risk_level": SRiskLevel.LOW, "risk_score": 0.05, "author": "医药记者",
         "publish_time": datetime.now() - timedelta(days=4), "monitor_id": MONITOR_IDS[0],
         "summary": "正面消息，尽调目标公司重大利好。"},
        {"title": "XX科技被前员工起诉商业秘密纠纷", "content": "XX科技发展有限公司前高管起诉公司侵犯其商业秘密权，要求赔偿300万元。",
         "keyword": "XX科技", "source": "法律界论坛", "source_type": SourceType.FORUM,
         "sentiment_type": SentimentType.NEGATIVE, "sentiment_score": -0.60,
         "risk_level": SRiskLevel.MEDIUM, "risk_score": 0.55, "author": "法律观察者",
         "publish_time": datetime.now() - timedelta(days=6), "monitor_id": MONITOR_IDS[0],
         "summary": "中性偏负面，客户公司面临商业秘密诉讼。"},
        # 法律行业动态
        {"title": "最高法发布新一批民法典司法解释", "content": "最高人民法院发布《关于适用民法典合同编若干问题的解释（二）》，对合同效力、违约责任等问题作出新规定。",
         "keyword": "司法解释", "source": "最高人民法院官网", "source_type": SourceType.OFFICIAL,
         "sentiment_type": SentimentType.NEUTRAL, "sentiment_score": 0.20,
         "risk_level": SRiskLevel.LOW, "risk_score": 0.0, "author": "最高人民法院",
         "publish_time": datetime.now() - timedelta(days=7), "monitor_id": MONITOR_IDS[1],
         "summary": "法律动态，新司法解释发布，需更新知识库。"},
        {"title": "律师行业数字化转型报告发布", "content": "中国律师协会发布《2026年律师行业数字化转型白皮书》，指出AI技术正深刻改变法律服务模式。",
         "keyword": "律师行业", "source": "中国律师网", "source_type": SourceType.OFFICIAL,
         "sentiment_type": SentimentType.POSITIVE, "sentiment_score": 0.50,
         "risk_level": SRiskLevel.LOW, "risk_score": 0.0, "author": "中国律师协会",
         "publish_time": datetime.now() - timedelta(days=10), "monitor_id": MONITOR_IDS[1],
         "summary": "行业趋势报道，AI在法律服务中的应用日益普及。"},
        {"title": "全国法院2025年度审判工作报告", "content": "最高人民法院工作报告显示，2025年全国法院审结各类案件3200万件，同比增长8.5%。",
         "keyword": "法治", "source": "人民日报", "source_type": SourceType.NEWS,
         "sentiment_type": SentimentType.NEUTRAL, "sentiment_score": 0.30,
         "risk_level": SRiskLevel.LOW, "risk_score": 0.0, "author": "人民日报记者",
         "publish_time": datetime.now() - timedelta(days=14), "monitor_id": MONITOR_IDS[1],
         "summary": "行业数据报告，反映司法审判工作总体态势。"},
        {"title": "个人信息保护法实施细则征求意见", "content": "国家互联网信息办公室发布《个人信息保护法实施细则（征求意见稿）》，进一步细化个人信息处理规则。",
         "keyword": "法律法规", "source": "国家网信办", "source_type": SourceType.OFFICIAL,
         "sentiment_type": SentimentType.NEUTRAL, "sentiment_score": 0.15,
         "risk_level": SRiskLevel.LOW, "risk_score": 0.0, "author": "国家网信办",
         "publish_time": datetime.now() - timedelta(days=8), "monitor_id": MONITOR_IDS[1],
         "summary": "政策动态，个保法细则征求意见，需关注对数据合规业务的影响。"},
    ]

    for r in records_data:
        session.add(SentimentRecord(
            id=uid(), title=r["title"], content=r["content"],
            keyword=r["keyword"], source=r.get("source"),
            source_type=r.get("source_type", SourceType.OTHER),
            sentiment_type=r.get("sentiment_type", SentimentType.NEUTRAL),
            sentiment_score=r.get("sentiment_score", 0.0),
            risk_level=r.get("risk_level", SRiskLevel.LOW),
            risk_score=r.get("risk_score", 0.0),
            summary=r.get("summary"), author=r.get("author"),
            publish_time=r.get("publish_time"),
            org_id=ORG_ID, monitor_id=r.get("monitor_id"),
        ))
    print(f"  + {len(records_data)} 条舆情记录")

    # 舆情预警
    alerts_data = [
        {"alert_type": AlertType.HIGH_RISK, "alert_level": AlertLevel.CRITICAL,
         "title": "HH上市公司重大负面舆情", "message": "HH上市公司被证监会立案调查，风险评分0.95。建议立即启动应急预案。",
         "is_read": False, "is_handled": False, "monitor_id": MONITOR_IDS[0]},
        {"alert_type": AlertType.NEGATIVE_SURGE, "alert_level": AlertLevel.WARNING,
         "title": "DD地产负面舆情激增", "message": "DD地产相关负面舆情在24小时内增长200%，社交媒体传播量大。",
         "is_read": True, "is_handled": False, "monitor_id": MONITOR_IDS[0]},
        {"alert_type": AlertType.KEYWORD_MATCH, "alert_level": AlertLevel.INFO,
         "title": "XX科技商业秘密诉讼", "message": "监控到XX科技被前员工起诉商业秘密纠纷，建议关注案件进展。",
         "is_read": True, "is_handled": True, "monitor_id": MONITOR_IDS[0]},
    ]

    for a in alerts_data:
        session.add(SentimentAlert(
            id=uid(), alert_type=a["alert_type"], alert_level=a["alert_level"],
            title=a["title"], message=a["message"],
            is_read=a.get("is_read", False), is_handled=a.get("is_handled", False),
            org_id=ORG_ID, monitor_id=a.get("monitor_id"),
        ))
    print(f"  + {len(alerts_data)} 条舆情预警")


if __name__ == "__main__":
    asyncio.run(seed())
