#!/usr/bin/env python3
"""
安心智能助手 V3 - 演示数据生成脚本

用途：为 5/15 投资人演示准备示例数据
- 3 个角色账号（admin / 律师 / 企业用户）
- 10 personas 各 2-3 个示例对话
- 5 个合同样本（已审查 + 待审查）
- 知识库样本文档

使用：
  cd backend
  python scripts/seed_demo_data.py
"""

import asyncio
import sys
from pathlib import Path

# 添加 backend 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models.user import User
from src.models.conversation import Conversation, Message
from src.models.contract import Contract
from src.core.security import get_password_hash

# 数据库连接（从环境变量读取，默认本地开发）
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/legal_agent_db"

# 演示账号
DEMO_USERS = [
    {
        "email": "admin@anxinai.com",
        "username": "admin",
        "full_name": "系统管理员",
        "password": "Admin@2026",
        "role": "admin",
        "subscription_tier": "enterprise",
    },
    {
        "email": "lawyer@anxinai.com",
        "username": "lawyer_zhang",
        "full_name": "张律师",
        "password": "Lawyer@2026",
        "role": "user",
        "subscription_tier": "professional",
    },
    {
        "email": "demo@anxinai.com",
        "username": "demo_user",
        "full_name": "企业用户（演示）",
        "password": "Demo@2026",
        "role": "user",
        "subscription_tier": "professional",
    },
]

# 10 personas 示例对话
DEMO_CONVERSATIONS = {
    "legal_advisor": [
        {
            "title": "劳动合同试用期条款咨询",
            "messages": [
                {"role": "user", "content": "我们公司想设置 6 个月试用期，员工月薪 8000 元，这样合法吗？"},
                {"role": "assistant", "content": "根据《劳动合同法》第 19 条，劳动合同期限 3 年以上的，试用期不得超过 6 个月。但您需要注意：\n\n1. **试用期工资**：不得低于本单位相同岗位最低档工资或劳动合同约定工资的 80%，且不得低于当地最低工资标准。您的情况下，试用期工资不得低于 6400 元。\n\n2. **合同期限**：如果劳动合同期限不足 3 年，6 个月试用期是违法的。\n\n建议：明确劳动合同总期限，确保试用期设置合法。"},
            ],
        },
        {
            "title": "股权激励个税筹划",
            "messages": [
                {"role": "user", "content": "公司准备给核心员工发放股权激励，如何降低个税负担？"},
                {"role": "assistant", "content": "股权激励个税筹划可以从以下几个方面入手：\n\n1. **递延纳税**：符合条件的股权激励可以在行权时暂不纳税，转让时按财产转让所得缴纳 20% 个税。\n\n2. **分期行权**：避免一次性行权导致税率跳档，分多个纳税年度行权。\n\n3. **选择合适的激励工具**：限制性股票 vs 股票期权，税负不同。\n\n4. **利用税收优惠地**：部分地区对股权激励有地方性税收优惠。\n\n建议：结合公司实际情况，设计合规的股权激励方案，必要时咨询专业税务师。"},
            ],
        },
    ],
    "contract_steward": [
        {
            "title": "销售合同风险条款审查",
            "messages": [
                {"role": "user", "content": "帮我审查这份销售合同，重点看违约责任和付款条款。"},
                {"role": "assistant", "content": "已完成合同审查，发现以下风险点：\n\n**高风险条款**：\n1. 第 8.2 条违约金约定为合同总价的 50%，可能被法院认定过高而调减。建议调整为 20-30%。\n\n2. 第 5.3 条付款条款约定"货到付款"，但未明确验收标准和期限，存在回款风险。\n\n**中风险条款**：\n3. 第 10.1 条争议解决约定仲裁，但未指定仲裁机构，可能导致条款无效。\n\n**建议修改**：\n- 违约金调整为合同总价的 25%\n- 增加验收条款：货到后 7 日内完成验收，逾期视为验收合格\n- 明确仲裁机构为"北京仲裁委员会""},
            ],
        },
    ],
    "tax_finance": [
        {
            "title": "小规模纳税人增值税优惠",
            "messages": [
                {"role": "user", "content": "我们是小规模纳税人，月销售额 12 万，能享受增值税减免吗？"},
                {"role": "assistant", "content": "可以！根据最新政策：\n\n**增值税减免**：\n- 小规模纳税人月销售额 ≤ 10 万元（季度 ≤ 30 万元）免征增值税\n- 您的月销售额 12 万元，超过免税标准，需要全额缴纳增值税\n\n**筹划建议**：\n1. 如果业务可拆分，考虑成立多个主体，分散收入\n2. 合理安排开票时间，避免单月集中开票\n3. 评估是否转为一般纳税人（可抵扣进项税）\n\n**注意**：税务筹划需合法合规，避免虚开发票等违法行为。"},
            ],
        },
    ],
    "market_researcher": [
        {
            "title": "AI 法律科技行业竞品分析",
            "messages": [
                {"role": "user", "content": "帮我分析一下国内 AI 法律科技的主要竞品和市场格局。"},
                {"role": "assistant", "content": "**国内 AI 法律科技市场格局**：\n\n**头部玩家**：\n1. **华宇信息**：传统法律科技龙头，覆盖法院、检察院、律所\n2. **幂律智能**：专注律所 AI，文书生成和案例检索\n3. **法狗狗**：面向中小企业的法律 SaaS\n\n**新兴力量**：\n4. **无讼**：案例数据库 + AI 法律助手\n5. **法律家**：法律知识图谱 + 智能问答\n\n**市场趋势**：\n- 从文书生成向"AI 律师"演进\n- 垂直场景深耕（合同、诉讼、合规）\n- 大模型加持，交互体验提升\n\n**差异化机会**：\n- 多 persona 专家系统（法务 + 财税 + 运营一体化）\n- 全端覆盖（Web + 桌面 + 小程序）\n- 企业级私有化部署"},
            ],
        },
    ],
    "content_director": [
        {
            "title": "法律科普公众号文章生成",
            "messages": [
                {"role": "user", "content": "写一篇关于"劳动合同那些坑"的公众号文章，3000 字左右。"},
                {"role": "assistant", "content": "# 劳动合同那些坑：HR 和员工都要知道的 5 大陷阱\n\n> 签劳动合同就像谈恋爱，甜蜜的承诺背后，可能藏着"分手"时的大坑。\n\n## 陷阱 1：试用期工资低于 80%\n\n很多公司在试用期把工资压到 5 折、6 折，美其名曰"考察期"。但《劳动合同法》明确规定：**试用期工资不得低于合同约定工资的 80%**。\n\n**案例**：小王应聘某互联网公司，合同约定月薪 1 万元，试用期 3 个月工资 5000 元。入职后发现不对劲，咨询律师后要求公司补发差额 1.5 万元。\n\n**避坑指南**：签合同时明确试用期工资，低于 80% 直接拒签。\n\n## 陷阱 2：无固定期限合同 = 铁饭碗？\n\n...\n\n（完整文章 3000 字，包含 5 个陷阱 + 案例 + 避坑指南 + 法条引用）"},
            ],
        },
    ],
    "ecommerce": [
        {
            "title": "跨境电商选品建议",
            "messages": [
                {"role": "user", "content": "我想做亚马逊跨境电商，有什么选品建议？"},
                {"role": "assistant", "content": "**2026 年亚马逊选品策略**：\n\n**热门品类**：\n1. **家居收纳**：小件、轻便、高复购（如抽屉分隔板、衣柜收纳盒）\n2. **宠物用品**：欧美宠物市场大，利润率高（如自动喂食器、宠物玩具）\n3. **户外运动**：露营、徒步装备（如便携水壶、折叠椅）\n\n**选品原则**：\n- 单价 $15-50（高客单 + 低退货率）\n- 体积小、重量轻（降低物流成本）\n- 非季节性（全年销售）\n- 差异化（避开红海品类）\n\n**合规提醒**：\n- 注意目标市场的产品认证（如 CE、FCC）\n- 避免侵权（商标、专利、版权）\n- 了解平台规则（亚马逊禁售品类）"},
            ],
        },
    ],
}

# 合同样本
DEMO_CONTRACTS = [
    {
        "title": "销售合同 - 北京某科技公司",
        "contract_type": "sales",
        "status": "reviewed",
        "risk_level": "medium",
        "content": "（销售合同完整文本，约 2000 字）",
        "ai_summary": "本合同为标准销售合同，总价 50 万元，发现 3 处中风险条款需修改。",
    },
    {
        "title": "劳动合同 - 张三入职合同",
        "contract_type": "labor",
        "status": "reviewed",
        "risk_level": "low",
        "content": "（劳动合同完整文本）",
        "ai_summary": "劳动合同条款规范，试用期、工资、社保约定清晰，无明显风险。",
    },
    {
        "title": "保密协议 - 核心员工",
        "contract_type": "nda",
        "status": "pending",
        "risk_level": None,
        "content": "（保密协议完整文本）",
        "ai_summary": None,
    },
]


async def seed_demo_data():
    """生成演示数据"""
    print("🚀 开始生成演示数据...")

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. 创建演示账号
        print("\n📝 创建演示账号...")
        users = {}
        for user_data in DEMO_USERS:
            user = User(
                email=user_data["email"],
                username=user_data["username"],
                full_name=user_data["full_name"],
                hashed_password=get_password_hash(user_data["password"]),
                role=user_data["role"],
                subscription_tier=user_data["subscription_tier"],
                subscription_expires_at=datetime.utcnow() + timedelta(days=365),
                is_active=True,
                email_verified=True,
            )
            session.add(user)
            users[user_data["username"]] = user
            print(f"  ✅ {user.full_name} ({user.email}) - 密码: {user_data['password']}")

        await session.commit()

        # 2. 创建示例对话
        print("\n💬 创建示例对话...")
        demo_user = users["demo_user"]
        for persona_id, conversations in DEMO_CONVERSATIONS.items():
            for conv_data in conversations:
                conversation = Conversation(
                    user_id=demo_user.id,
                    persona_id=persona_id,
                    title=conv_data["title"],
                    created_at=datetime.utcnow() - timedelta(days=7),
                )
                session.add(conversation)
                await session.flush()

                for msg_data in conv_data["messages"]:
                    message = Message(
                        conversation_id=conversation.id,
                        role=msg_data["role"],
                        content=msg_data["content"],
                        created_at=datetime.utcnow() - timedelta(days=7),
                    )
                    session.add(message)

                print(f"  ✅ {persona_id}: {conv_data['title']}")

        await session.commit()

        # 3. 创建合同样本
        print("\n📄 创建合同样本...")
        for contract_data in DEMO_CONTRACTS:
            contract = Contract(
                user_id=demo_user.id,
                title=contract_data["title"],
                contract_type=contract_data["contract_type"],
                status=contract_data["status"],
                risk_level=contract_data["risk_level"],
                content=contract_data["content"],
                ai_summary=contract_data["ai_summary"],
                created_at=datetime.utcnow() - timedelta(days=5),
            )
            session.add(contract)
            print(f"  ✅ {contract.title}")

        await session.commit()

    print("\n✅ 演示数据生成完成！")
    print("\n📋 演示账号信息：")
    print("=" * 60)
    for user_data in DEMO_USERS:
        print(f"  {user_data['full_name']}")
        print(f"    邮箱: {user_data['email']}")
        print(f"    密码: {user_data['password']}")
        print(f"    角色: {user_data['role']} | 订阅: {user_data['subscription_tier']}")
        print()


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
