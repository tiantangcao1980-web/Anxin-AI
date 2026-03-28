# -*- coding: utf-8 -*-
"""
测试账号种子脚本 — 覆盖所有用户角色和客户类型

⚠️ 仅用于开发和测试环境，项目上线前必须清理所有测试账号。
   账号密码信息不得外泄，不得提交到公共仓库。

运行: cd backend && python scripts/seed_test_roles.py

角色体系说明:
  - role: admin(系统管理员) / member(普通成员) / viewer(只读访客) / lawyer(认证律师)
  - user_type: internal(内部员工) / platform_lawyer(平台律师) / enterprise(企业用户) / individual(个人用户)
"""

import asyncio
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from src.core.database import async_session_maker, init_db
from src.models.user import User, Organization
from src.core.security import get_password_hash


# ===== 组织定义 =====
TEST_ORGS = [
    {
        "id": "00000000-0000-0000-0000-000000000001",
        "name": "安心法务科技有限公司",
        "description": "平台运营方",
    },
    {
        "id": "00000000-0000-0000-0000-000000000002",
        "name": "明德律师事务所",
        "description": "合作律所",
    },
    {
        "id": "00000000-0000-0000-0000-000000000003",
        "name": "鹏程科技集团有限公司",
        "description": "企业客户",
    },
]

# ===== 统一密码策略 =====
# 所有测试账号使用统一前缀 + 角色后缀，便于记忆和管理
# 格式: Anxin2026! + 角色缩写（例如 Anxin2026!Adm）
DEFAULT_PWD = "Anxin2026!"

# ===== 完整测试账号列表（16个角色） =====
TEST_ACCOUNTS = [
    # ========== 一、平台管理（internal） ==========
    {
        "email": "admin@anxin.test",
        "name": "超级管理员",
        "role": "admin",
        "user_type": "internal",
        "department": "技术部",
        "org_id": TEST_ORGS[0]["id"],
        "password": DEFAULT_PWD + "Adm",
    },
    {
        "email": "ops@anxin.test",
        "name": "运维工程师",
        "role": "admin",
        "user_type": "internal",
        "department": "技术部",
        "org_id": TEST_ORGS[0]["id"],
        "password": DEFAULT_PWD + "Ops",
    },
    {
        "email": "auditor@anxin.test",
        "name": "审计专员-周涛",
        "role": "viewer",
        "user_type": "internal",
        "department": "合规部",
        "org_id": TEST_ORGS[0]["id"],
        "password": DEFAULT_PWD + "Aud",
    },

    # ========== 二、律所管理（internal） ==========
    {
        "email": "director@mingde.test",
        "name": "律所主任-王建国",
        "role": "admin",
        "user_type": "internal",
        "department": "管理层",
        "org_id": TEST_ORGS[1]["id"],
        "password": DEFAULT_PWD + "Dir",
    },
    {
        "email": "partner@mingde.test",
        "name": "合伙人-李明华",
        "role": "member",
        "user_type": "internal",
        "department": "民商事部",
        "org_id": TEST_ORGS[1]["id"],
        "password": DEFAULT_PWD + "Ptn",
    },

    # ========== 三、平台认证律师（platform_lawyer） ==========
    {
        "email": "lawyer.zhang@anxin.test",
        "name": "张伟律师",
        "role": "lawyer",
        "user_type": "platform_lawyer",
        "department": "合同法",
        "org_id": TEST_ORGS[1]["id"],
        "password": DEFAULT_PWD + "Law",
    },
    {
        "email": "lawyer.li@anxin.test",
        "name": "李娜律师",
        "role": "lawyer",
        "user_type": "platform_lawyer",
        "department": "知识产权",
        "org_id": TEST_ORGS[1]["id"],
        "password": DEFAULT_PWD + "Law",
    },
    {
        "email": "lawyer.wang@anxin.test",
        "name": "王强律师",
        "role": "lawyer",
        "user_type": "platform_lawyer",
        "department": "劳动法",
        "org_id": TEST_ORGS[1]["id"],
        "password": DEFAULT_PWD + "Law",
    },

    # ========== 四、律所内部员工 ==========
    {
        "email": "senior@mingde.test",
        "name": "资深律师-陈明",
        "role": "member",
        "user_type": "internal",
        "department": "诉讼部",
        "org_id": TEST_ORGS[1]["id"],
        "password": DEFAULT_PWD + "Snr",
    },
    {
        "email": "assistant@mingde.test",
        "name": "律师助理-刘芳",
        "role": "member",
        "user_type": "internal",
        "department": "综合部",
        "org_id": TEST_ORGS[1]["id"],
        "password": DEFAULT_PWD + "Ast",
    },
    {
        "email": "intern@mingde.test",
        "name": "实习生-赵磊",
        "role": "viewer",
        "user_type": "internal",
        "department": "综合部",
        "org_id": TEST_ORGS[1]["id"],
        "password": DEFAULT_PWD + "Int",
    },

    # ========== 五、企业客户（enterprise） ==========
    {
        "email": "legal@pengcheng.test",
        "name": "法务总监-孙丽",
        "role": "member",
        "user_type": "enterprise",
        "department": "法务部",
        "org_id": TEST_ORGS[2]["id"],
        "password": DEFAULT_PWD + "Ent",
    },
    {
        "email": "compliance@pengcheng.test",
        "name": "合规经理-周强",
        "role": "member",
        "user_type": "enterprise",
        "department": "合规部",
        "org_id": TEST_ORGS[2]["id"],
        "password": DEFAULT_PWD + "Ent",
    },
    {
        "email": "ceo@pengcheng.test",
        "name": "企业管理员-钱总",
        "role": "admin",
        "user_type": "enterprise",
        "department": "管理层",
        "org_id": TEST_ORGS[2]["id"],
        "password": DEFAULT_PWD + "Ent",
    },

    # ========== 六、个人用户（individual） ==========
    {
        "email": "user.chen@test.com",
        "name": "陈小明",
        "role": "member",
        "user_type": "individual",
        "department": None,
        "org_id": None,
        "password": DEFAULT_PWD + "Usr",
    },
    {
        "email": "user.lin@test.com",
        "name": "林小红",
        "role": "member",
        "user_type": "individual",
        "department": None,
        "org_id": None,
        "password": DEFAULT_PWD + "Usr",
    },
    {
        "email": "visitor@test.com",
        "name": "访客体验",
        "role": "viewer",
        "user_type": "individual",
        "department": None,
        "org_id": None,
        "password": DEFAULT_PWD + "Vis",
    },
]


async def seed_orgs(session):
    """创建测试组织"""
    for org_def in TEST_ORGS:
        result = await session.execute(
            select(Organization).where(Organization.id == org_def["id"])
        )
        existing = result.scalar_one_or_none()
        if not existing:
            session.add(Organization(
                id=org_def["id"],
                name=org_def["name"],
                description=org_def["description"],
                is_active=True,
            ))
            print(f"  [组织+] {org_def['name']}")
        else:
            print(f"  [组织=] {org_def['name']}（已存在）")


async def seed_accounts(session):
    """创建测试账号"""
    created = 0
    updated = 0

    for acct in TEST_ACCOUNTS:
        result = await session.execute(
            select(User).where(User.email == acct["email"])
        )
        user = result.scalar_one_or_none()
        hashed = get_password_hash(acct["password"])

        if user:
            user.name = acct["name"]
            user.role = acct["role"]
            user.user_type = acct["user_type"]
            user.department = acct["department"]
            user.is_active = True
            updated += 1
        else:
            session.add(User(
                id=str(uuid4()),
                email=acct["email"],
                name=acct["name"],
                hashed_password=hashed,
                role=acct["role"],
                user_type=acct["user_type"],
                department=acct["department"],
                org_id=acct["org_id"],
                is_active=True,
            ))
            created += 1

    return created, updated


async def main():
    """主入口"""
    await init_db()

    async with async_session_maker() as session:
        print("\n  📦 创建测试组织...\n")
        await seed_orgs(session)

        print("\n  👥 创建测试账号...\n")
        created, updated = await seed_accounts(session)

        await session.commit()

        # 打印汇总
        print(f"\n  ✅ 完成: 新建 {created} 个, 更新 {updated} 个")
        print(f"\n  {'─' * 90}")
        print(f"  {'#':<3} {'邮箱':<32} {'姓名':<16} {'角色':<8} {'用户类型':<16} {'密码'}")
        print(f"  {'─' * 90}")
        for i, a in enumerate(TEST_ACCOUNTS, 1):
            print(f"  {i:<3} {a['email']:<32} {a['name']:<16} {a['role']:<8} {a['user_type']:<16} {a['password']}")
        print(f"  {'─' * 90}")
        print(f"\n  ⚠️  以上为测试账号，仅限开发环境使用，上线前必须清理！\n")


if __name__ == "__main__":
    print("\n  🔧 安心法务 - 测试账号初始化\n")
    asyncio.run(main())
