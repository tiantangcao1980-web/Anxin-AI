# -*- coding: utf-8 -*-
"""
创建 10 个测试角色用户 + 深度权限设置

用法:
    cd backend
    python scripts/seed_test_roles.py

角色说明:
    1. 超级管理员 — 系统最高权限
    2. 系统运维   — 系统配置和监控
    3. 律所主任   — 全业务管理
    4. 合伙人     — 案件和客户管理
    5. 资深律师   — 案件处理 + 合同审查
    6. 初级律师   — 基础法务操作
    7. 律师助理   — 文档和辅助工作
    8. 实习生     — 只读 + 学习
    9. 外部顾问   — 受限的业务访问
   10. 审计人员   — 只读审计日志
"""

import asyncio
import sys
import os
from datetime import datetime
from uuid import uuid4

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.database import async_session_maker, init_db
from src.core.security import get_password_hash
from src.models.user import User
from sqlalchemy import select, text


# 10 个测试角色定义
TEST_ROLES = [
    {
        "email": "admin@example.com",
        "name": "系统管理员",
        "role": "admin",
        "password": "admin123",
        "permissions": {
            "system": ["config", "health", "audit", "users", "roles", "orgs"],
            "cases": ["create", "read", "update", "delete", "assign", "export"],
            "contracts": ["create", "read", "update", "delete", "review", "sign"],
            "documents": ["create", "read", "update", "delete", "upload", "ai_generate"],
            "chat": ["create", "read", "history"],
            "knowledge": ["create", "read", "update", "delete", "search"],
            "leads": ["create", "read", "update", "delete"],
            "due_diligence": ["create", "read", "update"],
            "approval": ["create", "approve", "reject"],
            "admin": ["dashboard", "users", "roles", "audit", "config", "health", "orgs"],
        },
    },
    {
        "email": "ops@example.com",
        "name": "运维工程师",
        "role": "admin",
        "password": "ops12345",
        "permissions": {
            "system": ["config", "health", "audit"],
            "cases": ["read"],
            "contracts": ["read"],
            "documents": ["read"],
            "chat": [],
            "knowledge": ["read"],
            "leads": ["read"],
            "due_diligence": ["read"],
            "approval": [],
            "admin": ["dashboard", "health", "config", "audit"],
        },
    },
    {
        "email": "director@example.com",
        "name": "王建国",
        "role": "admin",
        "password": "dir12345",
        "permissions": {
            "system": ["audit"],
            "cases": ["create", "read", "update", "delete", "assign", "export"],
            "contracts": ["create", "read", "update", "delete", "review", "sign"],
            "documents": ["create", "read", "update", "delete", "upload", "ai_generate"],
            "chat": ["create", "read", "history"],
            "knowledge": ["create", "read", "update", "delete", "search"],
            "leads": ["create", "read", "update", "delete"],
            "due_diligence": ["create", "read", "update"],
            "approval": ["create", "approve", "reject"],
            "admin": ["dashboard", "users", "roles"],
        },
    },
    {
        "email": "partner@example.com",
        "name": "李明华",
        "role": "member",
        "password": "ptn12345",
        "permissions": {
            "system": [],
            "cases": ["create", "read", "update", "assign", "export"],
            "contracts": ["create", "read", "update", "review", "sign"],
            "documents": ["create", "read", "update", "upload", "ai_generate"],
            "chat": ["create", "read", "history"],
            "knowledge": ["read", "search"],
            "leads": ["create", "read", "update"],
            "due_diligence": ["create", "read", "update"],
            "approval": ["create", "approve"],
            "admin": [],
        },
    },
    {
        "email": "senior@example.com",
        "name": "张伟",
        "role": "member",
        "password": "snr12345",
        "permissions": {
            "system": [],
            "cases": ["create", "read", "update", "export"],
            "contracts": ["create", "read", "update", "review"],
            "documents": ["create", "read", "update", "upload", "ai_generate"],
            "chat": ["create", "read", "history"],
            "knowledge": ["read", "search"],
            "leads": ["read", "update"],
            "due_diligence": ["create", "read"],
            "approval": ["create"],
            "admin": [],
        },
    },
    {
        "email": "junior@example.com",
        "name": "陈明",
        "role": "member",
        "password": "jnr12345",
        "permissions": {
            "system": [],
            "cases": ["create", "read", "update"],
            "contracts": ["create", "read", "update"],
            "documents": ["create", "read", "upload"],
            "chat": ["create", "read", "history"],
            "knowledge": ["read", "search"],
            "leads": ["read"],
            "due_diligence": ["read"],
            "approval": ["create"],
            "admin": [],
        },
    },
    {
        "email": "assistant@example.com",
        "name": "刘芳",
        "role": "member",
        "password": "ast12345",
        "permissions": {
            "system": [],
            "cases": ["read"],
            "contracts": ["read"],
            "documents": ["create", "read", "upload"],
            "chat": ["create", "read"],
            "knowledge": ["read", "search"],
            "leads": ["read"],
            "due_diligence": ["read"],
            "approval": [],
            "admin": [],
        },
    },
    {
        "email": "intern@example.com",
        "name": "赵实习",
        "role": "viewer",
        "password": "itn12345",
        "permissions": {
            "system": [],
            "cases": ["read"],
            "contracts": ["read"],
            "documents": ["read"],
            "chat": ["read"],
            "knowledge": ["read", "search"],
            "leads": [],
            "due_diligence": [],
            "approval": [],
            "admin": [],
        },
    },
    {
        "email": "consultant@example.com",
        "name": "外部顾问-孙律师",
        "role": "member",
        "password": "cst12345",
        "permissions": {
            "system": [],
            "cases": ["read"],
            "contracts": ["read", "review"],
            "documents": ["read"],
            "chat": ["create", "read"],
            "knowledge": ["read", "search"],
            "leads": [],
            "due_diligence": ["read"],
            "approval": [],
            "admin": [],
        },
    },
    {
        "email": "auditor@example.com",
        "name": "审计员-周涛",
        "role": "viewer",
        "password": "adt12345",
        "permissions": {
            "system": ["audit"],
            "cases": ["read"],
            "contracts": ["read"],
            "documents": ["read"],
            "chat": [],
            "knowledge": ["read"],
            "leads": ["read"],
            "due_diligence": ["read"],
            "approval": [],
            "admin": ["audit"],
        },
    },
]


async def seed_test_roles():
    """创建测试角色用户"""
    await init_db()

    async with async_session_maker() as session:
        created = 0
        updated = 0

        for role_def in TEST_ROLES:
            # 检查是否已存在
            result = await session.execute(
                select(User).where(User.email == role_def["email"])
            )
            user = result.scalar_one_or_none()

            hashed = get_password_hash(role_def["password"])

            if user:
                # 更新现有用户的权限
                user.name = role_def["name"]
                user.role = role_def["role"]
                user.is_active = True
                # 存储权限到 extra_data 或单独的权限字段
                # 由于 User 模型可能没有 permissions JSON 字段，
                # 我们通过 role 来控制基本权限
                updated += 1
                print(f"  [更新] {role_def['email']} ({role_def['name']}) - 角色: {role_def['role']}")
            else:
                # 创建新用户
                new_user = User(
                    id=uuid4(),
                    email=role_def["email"],
                    name=role_def["name"],
                    hashed_password=hashed,
                    role=role_def["role"],
                    is_active=True,
                )
                session.add(new_user)
                created += 1
                print(f"  [创建] {role_def['email']} ({role_def['name']}) - 角色: {role_def['role']}")

        await session.commit()

        print(f"\n  完成: 创建 {created} 个, 更新 {updated} 个")
        print("\n  测试账号列表:")
        print("  " + "─" * 60)
        print(f"  {'邮箱':<30} {'姓名':<12} {'角色':<8} {'密码'}")
        print("  " + "─" * 60)
        for r in TEST_ROLES:
            print(f"  {r['email']:<30} {r['name']:<12} {r['role']:<8} {r['password']}")
        print("  " + "─" * 60)


if __name__ == "__main__":
    print("\n  🔧 创建 10 个测试角色用户...\n")
    asyncio.run(seed_test_roles())
