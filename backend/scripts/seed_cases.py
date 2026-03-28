import asyncio
import sys
import os
import uuid
from datetime import datetime, timedelta
import random

# 添加 backend 目录到 sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.database import get_db_context
from src.models.case import Case, CaseStatus, CasePriority, CaseType
from src.models.document import Document
from src.models.user import User
from sqlalchemy import select

async def seed_cases():
    async with get_db_context() as session:
        # 获取默认管理员用户
        result = await session.execute(select(User).where(User.email == "admin@example.com"))
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("未找到管理员用户，请先运行数据库初始化")
            return

        print(f"使用用户: {admin.name} ({admin.id})")

        # 检查是否已有案件数据
        result = await session.execute(select(Case))
        existing_cases = result.scalars().all()
        
        if len(existing_cases) > 0:
            print(f"数据库中已有 {len(existing_cases)} 个案件，跳过种子数据填充")
            # return # 暂时注释掉，以便可以追加数据

        # 定义一些示例案件
        cases_data = [
            {
                "title": "XX科技公司买卖合同纠纷案",
                "case_number": "2024-民初-001",
                "case_type": CaseType.CONTRACT,
                "status": CaseStatus.IN_PROGRESS,
                "priority": CasePriority.HIGH,
                "description": "涉及标的额 500 万的软件开发合同纠纷，主要争议点在于交付标准和验收流程。",
                "client": "XX科技发展有限公司",
                "opponent": "YY网络科技有限公司",
                "court": "北京市海淀区人民法院",
                "amount": 5000000.0,
                "deadline": datetime.now() + timedelta(days=30),
                "created_at": datetime.now() - timedelta(days=10),
            },
            {
                "title": "张三劳动争议仲裁案",
                "case_number": "2024-劳仲-005",
                "case_type": CaseType.LABOR,
                "status": CaseStatus.PENDING,
                "priority": CasePriority.MEDIUM,
                "description": "员工因违法解除劳动合同申请仲裁，要求支付赔偿金及未休年假工资。",
                "client": "张三",
                "opponent": "ZZ贸易有限公司",
                "court": "朝阳区劳动争议仲裁委员会",
                "amount": 150000.0,
                "deadline": datetime.now() + timedelta(days=15),
                "created_at": datetime.now() - timedelta(days=5),
            },
            {
                "title": "AA集团股权转让纠纷",
                "case_number": "2024-商初-012",
                "case_type": CaseType.CORPORATE,
                "status": CaseStatus.WAITING,
                "priority": CasePriority.HIGH,
                "description": "股权转让协议履行过程中，受让方未按期支付款项，且目标公司资产存在隐瞒。",
                "client": "AA投资集团",
                "opponent": "李四",
                "court": "上海市第一中级人民法院",
                "amount": 20000000.0,
                "deadline": datetime.now() + timedelta(days=60),
                "created_at": datetime.now() - timedelta(days=20),
            },
            {
                "title": "BB文化公司著作权侵权案",
                "case_number": "2024-知民初-008",
                "case_type": CaseType.IP,
                "status": CaseStatus.CLOSED,
                "priority": CasePriority.LOW,
                "description": "被告未经许可在网络平台传播原告享有著作权的短视频作品。",
                "client": "BB文化传播有限公司",
                "opponent": "CC信息技术有限公司",
                "court": "北京互联网法院",
                "amount": 50000.0,
                "deadline": datetime.now() - timedelta(days=5), # 已截止
                "created_at": datetime.now() - timedelta(days=60),
            }
        ]

        created_cases = []

        for case_data in cases_data:
            # 检查案件号是否存在
            existing = await session.execute(select(Case).where(Case.case_number == case_data["case_number"]))
            if existing.scalar_one_or_none():
                print(f"案件 {case_data['case_number']} 已存在，跳过")
                continue

            # 构造 parties 字段 (JSON)
            parties = {
                "client": [{"name": case_data["client"], "role": "plaintiff"}],
                "opponent": [{"name": case_data["opponent"], "role": "defendant"}]
            }

            new_case = Case(
                id=str(uuid.uuid4()),
                title=case_data["title"],
                case_number=case_data["case_number"],
                case_type=case_data["case_type"],
                status=case_data["status"],
                priority=case_data["priority"],
                description=case_data["description"],
                parties=parties,
                court=case_data["court"],
                amount=case_data["amount"],
                deadline=case_data["deadline"],
                assignee_id=admin.id, # 分配给管理员
                owner_id=admin.id,
                created_at=case_data["created_at"],
                updated_at=datetime.now()
            )
            session.add(new_case)
            created_cases.append(new_case)
            print(f"添加案件: {new_case.title}")

        # 提交案件，以便获取 ID
        await session.commit()

        # 添加示例文档
        if created_cases:
            docs_data = [
                {"name": "起诉状.docx", "type": "法律文书", "size": 125000},
                {"name": "证据清单.xlsx", "type": "证据材料", "size": 89000},
                {"name": "合同扫描件.pdf", "type": "证据材料", "size": 2300000},
                {"name": "律师函.pdf", "type": "法律文书", "size": 150000},
                {"name": "庭审笔录.docx", "type": "案件记录", "size": 45000},
            ]

            for case in created_cases:
                # 每个案件随机添加 2-4 个文档
                num_docs = random.randint(2, 4)
                selected_docs = random.sample(docs_data, num_docs)
                
                for doc_info in selected_docs:
                    new_doc = Document(
                        id=str(uuid.uuid4()),
                        case_id=case.id,
                        name=doc_info["name"],
                        doc_type=doc_info["type"],
                        content_type="application/octet-stream", # 模拟 MIME type
                        file_size=doc_info["size"],
                        storage_path=f"/mock/path/{case.id}/{doc_info['name']}", # 模拟路径
                        status="processed",
                        owner_id=admin.id,
                        created_at=datetime.now() - timedelta(days=random.randint(1, 5))
                    )
                    session.add(new_doc)
                    print(f"  为案件 {case.case_number} 添加文档: {new_doc.name}")

            await session.commit()
            print("文档添加完成")

if __name__ == "__main__":
    asyncio.run(seed_cases())
