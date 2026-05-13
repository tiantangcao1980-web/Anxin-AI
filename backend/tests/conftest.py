"""
Pytest配置和Fixtures
"""

import asyncio

# ============ 测试数据库配置 ============
import os
from collections.abc import AsyncGenerator
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

# 导入所有模型，确保 Base.metadata 包含完整的表定义
from src.models import (  # noqa: F401 — side-effect import
    AIAssistantConfig,
    AIAssistantFeedback,
    Approval,
    ApprovalTemplate,
    Asset,
    AuditLog,
    BillingPlan,
    Case,
    CaseAssignment,
    CaseEvent,
    Consultation,
    Contract,
    ContractAttachment,
    ContractClause,
    ContractRisk,
    Conversation,
    ConversationSummary,
    Course,
    CourseProgress,
    Delegation,
    Document,
    DocumentCollaborator,
    DocumentEdit,
    DocumentSession,
    DocumentSnapshot,
    DocumentVersion,
    Expert,
    FeatureFlag,
    IMConversation,
    IMMessage,
    IMParticipant,
    Invoice,
    KnowledgeBase,
    KnowledgeDocument,
    LawyerCertification,
    LawyerProfile,
    LawyerReview,
    LawyerServiceConfig,
    Lead,
    LLMConfig,
    McpServerConfig,
    Message,
    Notification,
    NotificationPreference,
    Organization,
    PasswordResetToken,
    PaymentOrderModel,
    Refund,
    SentimentAlert,
    SentimentMonitor,
    SentimentRecord,
    SkillEnabledVersion,
    SkillGovernanceAuditEvent,
    SkillGovernanceProposal,
    Subscription,
    SubscriptionEvent,
    SyncLog,
    Task,
    Team,
    TeamMember,
    TimeEntry,
    User,
)
from src.models.base import Base
from src.models.case import CasePriority, CaseStatus, CaseType

# P2: 注册 task_orchestrator 的 agent_tasks 表到 Base.metadata
# （独立子目录 ORM，不在 src.models.__init__ 集中导出，需在此处显式 import）
from src.services.task_orchestrator.models import Task as AgentTask  # noqa: F401


# ============ 测试数据库配置 ============

import os

# 优先从环境变量获取测试数据库 URL
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///:memory:"
)

# 如果是 PostgreSQL，确保使用 asyncpg 驱动
if TEST_DATABASE_URL.startswith("postgresql://"):
    TEST_DATABASE_URL = TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# 创建测试引擎
# SQLite 内存数据库必须使用 StaticPool 保证所有连接共享同一个数据库实例
_is_sqlite_memory = ":memory:" in TEST_DATABASE_URL or "mode=memory" in TEST_DATABASE_URL
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool if _is_sqlite_memory else NullPool,
    **( {"connect_args": {"check_same_thread": False}} if _is_sqlite_memory else {} ),
)

# 创建测试会话工厂
test_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ============ Event Loop配置 ============

@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    """使用 pytest-asyncio 推荐的事件循环策略入口。"""
    return asyncio.DefaultEventLoopPolicy()


# ============ 认证风控开关隔离 ============
#
# `.env` 可能开启 CAPTCHA_ENABLED 以便本地/预发挥做人机校验，但自动化测试
# 默认不提供 captcha token，也不 mock 第三方验证服务。为保证测试基线稳定，
# 每个测试运行时强制关闭 CAPTCHA；个别测试（test_auth_surface_hardening.py
# 中的 captcha 用例）会通过 monkeypatch 再显式打开。

@pytest.fixture(autouse=True)
def _disable_captcha_by_default(monkeypatch):
    from src.core.config import settings as _settings

    monkeypatch.setattr(_settings, "CAPTCHA_ENABLED", False, raising=False)
    yield


# ============ 重置全局限流器状态（防止测试间污染） ============

@pytest_asyncio.fixture(autouse=True)
async def _reset_rate_limiter():
    """每个测试前重置限流状态（Redis + 本地内存），避免跨测试/跨运行干扰。"""
    from src.core.security import get_rate_limiter
    limiter = get_rate_limiter()
    limiter._memory_windows.clear()
    # 同时清理 Redis 中的限流键
    try:
        redis_client = await limiter._get_redis()
        keys = []
        async for key in redis_client.scan_iter(f"{limiter.KEY_PREFIX}:*"):
            keys.append(key)
        if keys:
            await redis_client.delete(*keys)
    except Exception:
        pass  # Redis 不可用时跳过
    yield
    limiter._memory_windows.clear()


# ============ 数据库Fixtures ============

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """
    在整个测试会话开始前创建所有表，结束后清理
    """
    async with test_engine.begin() as conn:
        # 先尝试删除旧表，确保环境干净
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    创建测试数据库会话
    
    每个测试函数都会获得一个干净的事务，测试结束后回滚
    """
    async with test_session_maker() as session:
        try:
            yield session
            await session.rollback() # 始终回滚以保持测试间的隔离
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture(scope="function")
async def db(db_session: AsyncSession) -> AsyncSession:
    """db_session的别名，方便使用"""
    return db_session


# ============ 测试客户端Fixtures ============

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    创建测试HTTP客户端
    """
    from src.api.main import app
    from src.core.database import get_db

    # 覆盖数据库依赖
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # 清理依赖覆盖
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def auth_client(
    db_session: AsyncSession,
    test_user: User,
) -> AsyncGenerator[AsyncClient, None]:
    """
    创建带认证的测试HTTP客户端
    """
    from src.api.main import app
    from src.core.database import get_db
    from src.core.security import create_access_token

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    token = create_access_token(user_id=test_user.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def admin_auth_client(
    db_session: AsyncSession,
    test_admin: User,
) -> AsyncGenerator[AsyncClient, None]:
    """
    创建带管理员认证的测试HTTP客户端
    """
    from src.api.main import app
    from src.core.database import get_db
    from src.core.security import create_access_token

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    token = create_access_token(user_id=test_admin.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ============ 用户Fixtures ============

@pytest_asyncio.fixture
async def test_organization(db_session: AsyncSession) -> Organization:
    """创建测试组织"""
    org = Organization(
        id=str(uuid4()),
        name="测试法务公司",
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_organization: Organization) -> User:
    """创建测试用户"""
    user = User(
        id=str(uuid4()),
        email=f"test-{uuid4().hex[:8]}@example.com",
        name="测试用户",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession, test_organization: Organization) -> User:
    """创建测试管理员"""
    admin = User(
        id=str(uuid4()),
        email=f"admin-{uuid4().hex[:8]}@anxinassistant.com",
        name="超级管理员",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="admin",
    )
    db_session.add(admin)
    await db_session.flush()
    return admin


# ============ 案件Fixtures ============

@pytest_asyncio.fixture
async def test_case(db_session: AsyncSession, test_user: User, test_organization: Organization) -> Case:
    """创建测试案件"""
    case = Case(
        id=str(uuid4()),
        title="测试合同纠纷案件",
        case_number=f"CASE-{datetime.now().strftime('%Y%m%d')}-TEST",
        case_type=CaseType.CONTRACT,
        status=CaseStatus.PENDING,
        priority=CasePriority.MEDIUM,
        description="这是一个测试案件，用于单元测试",
        org_id=test_organization.id,
        created_by=test_user.id,
    )
    db_session.add(case)
    await db_session.flush()
    return case


@pytest_asyncio.fixture
async def test_cases(db_session: AsyncSession, test_user: User, test_organization: Organization) -> list[Case]:
    """创建多个测试案件"""
    cases = []
    for i in range(5):
        case = Case(
            id=str(uuid4()),
            title=f"测试案件 {i+1}",
            case_number=f"CASE-TEST-{i+1:04d}",
            case_type=CaseType.CONTRACT if i % 2 == 0 else CaseType.LABOR,
            status=CaseStatus.PENDING if i < 3 else CaseStatus.IN_PROGRESS,
            priority=CasePriority.MEDIUM,
            description=f"测试案件描述 {i+1}",
            org_id=test_organization.id,
            created_by=test_user.id,
        )
        db_session.add(case)
        cases.append(case)

    await db_session.flush()
    return cases


# ============ 文档Fixtures ============

@pytest_asyncio.fixture
async def test_document(db_session: AsyncSession, test_user: User, test_organization: Organization) -> Document:
    """创建测试文档"""
    from src.models.document import DocumentType

    doc = Document(
        id=str(uuid4()),
        name="测试合同.pdf",
        doc_type=DocumentType.CONTRACT,
        file_path="/uploads/test_contract.pdf",
        file_size=1024,
        org_id=test_organization.id,
        created_by=test_user.id,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


# ============ 舆情Fixtures ============

@pytest_asyncio.fixture
async def test_monitor(db_session: AsyncSession, test_user: User, test_organization: Organization) -> SentimentMonitor:
    """创建测试监控配置"""
    monitor = SentimentMonitor(
        id=str(uuid4()),
        name="测试舆情监控",
        keywords=["法务", "合同纠纷", "知识产权"],
        sources=["news", "social_media"],
        alert_threshold=0.7,
        negative_threshold=0.6,
        risk_threshold=0.8,
        org_id=test_organization.id,
        created_by=test_user.id,
    )
    db_session.add(monitor)
    await db_session.flush()
    return monitor


@pytest_asyncio.fixture
async def test_sentiment_records(
    db_session: AsyncSession,
    test_monitor: SentimentMonitor,
    test_organization: Organization
) -> list[SentimentRecord]:
    """创建测试舆情记录"""
    records = []
    from src.models.sentiment import RiskLevel, SentimentType, SourceType

    test_data = [
        ("正面新闻", "公司获得行业最佳法务团队奖", "positive", 0.8, "low", 0.1),
        ("负面新闻", "公司涉嫌合同违约被起诉", "negative", -0.7, "high", 0.8),
        ("中性报道", "公司法务部门进行常规培训", "neutral", 0.0, "low", 0.2),
    ]

    for title, content, sentiment, score, risk, risk_score in test_data:
        record = SentimentRecord(
            id=str(uuid4()),
            keyword="法务",
            title=title,
            content=content,
            sentiment_type=SentimentType(sentiment),
            sentiment_score=score,
            risk_level=RiskLevel(risk),
            risk_score=risk_score,
            source_type=SourceType.NEWS,
            monitor_id=test_monitor.id,
            org_id=test_organization.id,
        )
        db_session.add(record)
        records.append(record)

    await db_session.flush()
    return records


# ============ 协作Fixtures ============

@pytest_asyncio.fixture
async def test_session(
    db_session: AsyncSession,
    test_document: Document,
    test_user: User
) -> DocumentSession:
    """创建测试协作会话"""
    from src.models.collaboration import CollaboratorRole, SessionStatus

    session = DocumentSession(
        id=str(uuid4()),
        document_id=test_document.id,
        name="测试协作会话",
        status=SessionStatus.ACTIVE,
        max_collaborators=10,
        created_by=test_user.id,
        base_content="这是测试文档内容",
        current_content="这是测试文档内容",
    )
    db_session.add(session)
    await db_session.flush()

    collaborator = DocumentCollaborator(
        id=str(uuid4()),
        session_id=session.id,
        user_id=test_user.id,
        role=CollaboratorRole.OWNER,
        nickname=test_user.name,
        color="#4ECDC4",
        is_online=False,
    )
    db_session.add(collaborator)
    await db_session.flush()
    return session


# ============ Mock Fixtures ============

@pytest.fixture
def mock_llm_response():
    """Mock LLM响应"""
    return {
        "content": "这是一个模拟的LLM响应",
        "model": "gpt-4o",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50}
    }


@pytest.fixture
def mock_agent():
    """Mock智能体"""
    agent = MagicMock()
    agent.chat = AsyncMock(return_value="这是模拟的智能体回复")
    agent.process = AsyncMock(return_value=MagicMock(
        agent_name="MockAgent",
        content="模拟处理结果",
        reasoning="模拟推理过程",
    ))
    return agent


@pytest.fixture
def mock_workforce():
    """Mock智能体团队"""
    workforce = MagicMock()
    workforce.chat = AsyncMock(return_value="这是模拟的团队回复")
    workforce.process_task = AsyncMock(return_value={
        "task": "测试任务",
        "analysis": {"agents": ["legal_advisor"]},
        "agent_results": [],
        "final_result": {"summary": "模拟分析结果"}
    })
    return workforce


# ============ 辅助函数 ============

def create_auth_headers(user: User) -> dict:
    """创建认证头（用于需要认证的API测试）"""
    from src.core.security import create_access_token
    token = create_access_token(user_id=user.id)
    return {"Authorization": f"Bearer {token}"}


# ============ Persona Registry Fixture（P11-C：避免单例污染） ============
#
# 测试套件里若多个测试共享同一 PersonaRegistry 单例，会出现：
#   1) test_persona_registry.py 的 _reset_registry fixture 销毁单例
#   2) 后续 personas API 测试通过 routes 层 _AUTOLOADED guard 跳过 autoload
#   3) registry 仍空 → 503/404
# 这里提供一个显式 fixture，让需要隔离的测试主动声明，每次给一份干净的
# registry（reset → 自动 bootstrap）。reset_instance 内部已会复位 routes
# 层 _AUTOLOADED guard，因此对 API 测试同样安全。

@pytest.fixture
def fresh_persona_registry():
    """每个测试前后重置 registry，避免单例污染。"""
    from src.agents.personas.registry import PersonaRegistry

    PersonaRegistry.reset_instance()
    yield PersonaRegistry.instance()
    PersonaRegistry.reset_instance()


async def create_test_data(db: AsyncSession, count: int = 10) -> dict:
    """批量创建测试数据"""
    org = Organization(
        id=str(uuid4()),
        name="批量测试组织",
    )
    db.add(org)

    user = User(
        id=str(uuid4()),
        email="batch@example.com",
        name="批量测试用户",
        hashed_password="hashed",
        org_id=org.id,
    )
    db.add(user)

    cases = []
    for i in range(count):
        case = Case(
            id=str(uuid4()),
            title=f"批量案件 {i+1}",
            case_number=f"BATCH-{i+1:04d}",
            case_type=CaseType.CONTRACT,
            org_id=org.id,
            created_by=user.id,
        )
        db.add(case)
        cases.append(case)

    await db.flush()

    return {
        "organization": org,
        "user": user,
        "cases": cases,
    }
