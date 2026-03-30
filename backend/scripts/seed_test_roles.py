# -*- coding: utf-8 -*-
"""
测试账号种子脚本 — 覆盖所有用户角色和客户类型

运行: cd backend && python scripts/seed_test_roles.py
"""

import asyncio
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from src.core.database import async_session_maker, engine
from src.models.user import User, Organization
from src.core.security import get_password_hash


# ===== 组织 =====
TEST_ORGS = [
    {"id": "00000000-0000-0000-0000-000000000001", "name": "安心法务科技有限公司", "description": "平台运营方"},
    {"id": "00000000-0000-0000-0000-000000000002", "name": "明德律师事务所", "description": "合作律所"},
    {"id": "00000000-0000-0000-0000-000000000003", "name": "鹏程科技集团有限公司", "description": "企业客户"},
]

# ===== 账号（简单好记的密码） =====
TEST_ACCOUNTS = [
    # 平台管理
    {"email": "admin@anxinfawu.com",      "name": "超级管理员",        "role": "admin",  "user_type": "internal",        "department": "技术部",   "org_id": TEST_ORGS[0]["id"], "password": "admin888"},
    {"email": "ops@anxinfawu.com",        "name": "运维工程师",        "role": "admin",  "user_type": "internal",        "department": "技术部",   "org_id": TEST_ORGS[0]["id"], "password": "ops888"},
    {"email": "auditor@anxinfawu.com",    "name": "审计专员-周涛",     "role": "viewer", "user_type": "internal",        "department": "合规部",   "org_id": TEST_ORGS[0]["id"], "password": "audit888"},
    # 律所管理
    {"email": "director@anxinfawu.com",   "name": "律所主任-王建国",   "role": "org_admin", "user_type": "internal",     "department": "管理层",   "org_id": TEST_ORGS[1]["id"], "password": "dir888"},
    {"email": "partner@anxinfawu.com",    "name": "合伙人-李明华",     "role": "partner", "user_type": "internal",        "department": "民商事部", "org_id": TEST_ORGS[1]["id"], "password": "partner888"},
    # 平台律师
    {"email": "zhangwei@anxinfawu.com",   "name": "张伟律师",          "role": "platform_lawyer", "user_type": "platform_lawyer", "department": "合同法",   "org_id": TEST_ORGS[1]["id"], "password": "lawyer888"},
    {"email": "lina@anxinfawu.com",       "name": "李娜律师",          "role": "platform_lawyer", "user_type": "platform_lawyer", "department": "知识产权", "org_id": TEST_ORGS[1]["id"], "password": "lawyer888"},
    {"email": "wangqiang@anxinfawu.com",  "name": "王强律师",          "role": "platform_lawyer", "user_type": "platform_lawyer", "department": "劳动法",   "org_id": TEST_ORGS[1]["id"], "password": "lawyer888"},
    # 律所员工
    {"email": "chenming@anxinfawu.com",   "name": "资深律师-陈明",     "role": "lawyer", "user_type": "internal",        "department": "诉讼部",   "org_id": TEST_ORGS[1]["id"], "password": "senior888"},
    {"email": "liufang@anxinfawu.com",    "name": "律师助理-刘芳",     "role": "paralegal", "user_type": "internal",     "department": "综合部",   "org_id": TEST_ORGS[1]["id"], "password": "assist888"},
    {"email": "zhaolei@anxinfawu.com",    "name": "实习生-赵磊",       "role": "viewer", "user_type": "internal",        "department": "综合部",   "org_id": TEST_ORGS[1]["id"], "password": "intern888"},
    # 企业客户
    {"email": "sunli@anxinfawu.com",      "name": "法务总监-孙丽",     "role": "enterprise_user", "user_type": "enterprise", "department": "法务部",   "org_id": TEST_ORGS[2]["id"], "password": "enter888"},
    {"email": "zhouqiang@anxinfawu.com",  "name": "合规经理-周强",     "role": "enterprise_user", "user_type": "enterprise", "department": "合规部",   "org_id": TEST_ORGS[2]["id"], "password": "enter888"},
    {"email": "boss@anxinfawu.com",       "name": "企业管理员-钱总",   "role": "org_admin", "user_type": "enterprise",   "department": "管理层",   "org_id": TEST_ORGS[2]["id"], "password": "enter888"},
    # 个人用户
    {"email": "xiaoming@anxinfawu.com",   "name": "陈小明",            "role": "individual_user", "user_type": "individual", "department": None,       "org_id": None,               "password": "user888"},
    {"email": "xiaohong@anxinfawu.com",   "name": "林小红",            "role": "individual_user", "user_type": "individual", "department": None,       "org_id": None,               "password": "user888"},
    {"email": "visitor@anxinfawu.com",    "name": "访客体验",          "role": "viewer", "user_type": "individual",      "department": None,       "org_id": None,               "password": "visit888"},
]


async def main():
    # 不调用 init_db()（避免 create_all 的外键冲突），直接用 session
    async with async_session_maker() as session:
        # 创建组织
        print("\n  📦 创建测试组织...\n")
        for org_def in TEST_ORGS:
            result = await session.execute(select(Organization).where(Organization.id == org_def["id"]))
            if not result.scalar_one_or_none():
                session.add(Organization(id=org_def["id"], name=org_def["name"], description=org_def["description"], is_active=True))
                print(f"  [+] {org_def['name']}")
            else:
                existing = await session.execute(select(Organization).where(Organization.id == org_def["id"]))
                org = existing.scalar_one()
                org.name = org_def["name"]
                print(f"  [=] {org_def['name']}（已存在）")

        # 创建账号
        print("\n  👥 创建测试账号...\n")
        created, updated = 0, 0
        for acct in TEST_ACCOUNTS:
            result = await session.execute(select(User).where(User.email == acct["email"]))
            user = result.scalar_one_or_none()
            hashed = get_password_hash(acct["password"])
            if user:
                user.name = acct["name"]
                user.role = acct["role"]
                user.user_type = acct["user_type"]
                user.department = acct["department"]
                user.hashed_password = hashed
                user.is_active = True
                updated += 1
            else:
                session.add(User(
                    id=str(uuid4()), email=acct["email"], name=acct["name"],
                    hashed_password=hashed, role=acct["role"], user_type=acct["user_type"],
                    department=acct["department"], org_id=acct["org_id"], is_active=True,
                ))
                created += 1

        await session.commit()

        # 打印汇总
        print(f"\n  ✅ 完成: 新建 {created} 个, 更新 {updated} 个")
        print(f"\n  {'─' * 80}")
        print(f"  {'#':<3} {'邮箱':<30} {'姓名':<16} {'角色':<8} {'密码':<12} {'类型'}")
        print(f"  {'─' * 80}")
        for i, a in enumerate(TEST_ACCOUNTS, 1):
            print(f"  {i:<3} {a['email']:<30} {a['name']:<16} {a['role']:<8} {a['password']:<12} {a['user_type']}")
        print(f"  {'─' * 80}\n")


if __name__ == "__main__":
    print("\n  🔧 安心法务 - 测试账号初始化\n")
    asyncio.run(main())
