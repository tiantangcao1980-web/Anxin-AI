from src.models.approval import Approval, ApprovalTemplate
from src.models.audit import AuditLog
from src.models.case import Case, CaseEvent
from src.models.case_market import CaseRequest
from src.models.collaboration import DocumentCollaborator, DocumentEdit, DocumentSession
from src.models.conversation import Conversation, Message, MessageRole
from src.models.course import Course, CourseProgress
from src.models.document import Document
from src.models.expert import Expert
from src.models.feature_flag import FeatureFlag
from src.models.firm_management import Invoice
from src.models.im import IMConversation, IMMessage
from src.models.knowledge import KnowledgeBase, KnowledgeDocument
from src.models.lawyer_certification import LawyerServiceConfig
from src.models.lawyer_matching import Consultation, LawyerProfile
from src.models.lead import Lead
from src.models.llm_config import LLMConfig
from src.models.mcp_config import McpServerConfig
from src.models.meeting_record import MeetingRecord
from src.models.review import LawyerReview
from src.models.task import Task
from src.models.user import User


def test_json_backed_models_accept_structured_defaults():
    review = LawyerReview(rating=5, tags=["专业", "高效"])
    meeting = MeetingRecord(
        conversation_id="conv-1",
        conversation_type="im",
        started_by="user-1",
        summary={"topic": "合同审查"},
        insights=[{"risk": "low"}],
        action_items=[{"task": "发送纪要"}],
    )
    mcp = McpServerConfig(
        name="local-tool",
        args=["run"],
        env={"ENV": "test"},
        cached_tools=[{"name": "search"}],
    )
    llm = LLMConfig(name="Local", provider="ollama", model_name="qwen")

    assert review.tags == ["专业", "高效"]
    assert meeting.summary == {"topic": "合同审查"}
    assert meeting.insights == [{"risk": "low"}]
    assert mcp.cached_tools == [{"name": "search"}]
    assert repr(llm) == "<LLMConfig Local (ollama/qwen)>"


def test_additional_json_models_accept_typed_payloads():
    profile = LawyerProfile(
        real_name="张律师",
        license_number="L-1",
        specializations=["劳动法"],
        available_hours={"mon": "09:00-18:00"},
    )
    consultation = Consultation(
        user_id="user-1",
        legal_tags=["合同"],
    )
    service_config = LawyerServiceConfig(
        lawyer_profile_id="profile-1",
        service_types=["instant_consultation"],
        working_hours={"mon": "09:00-18:00"},
    )
    knowledge_base = KnowledgeBase(
        name="合同库",
        config={"scope": "contract"},
    )
    knowledge_doc = KnowledgeDocument(
        title="服务合同",
        content="合同内容",
        extra_metadata={"source": "upload"},
        tags=["合同"],
    )
    conversation = IMConversation(
        type="private",
        metadata_={"source": "test"},
    )
    message = IMMessage(
        conversation_id="conv-1",
        sender_id="user-1",
        content="hello",
        metadata_={"attachments": []},
        read_by=["user-2"],
    )

    assert profile.specializations == ["劳动法"]
    assert consultation.legal_tags == ["合同"]
    assert service_config.service_types == ["instant_consultation"]
    assert knowledge_base.config == {"scope": "contract"}
    assert knowledge_doc.tags == ["合同"]
    assert conversation.metadata_ == {"source": "test"}
    assert message.read_by == ["user-2"]


def test_more_json_backed_models_accept_typed_payloads():
    invoice = Invoice(
        number="INV-1",
        client_name="安心客户",
        total_amount=1000,
        items=[{"description": "咨询", "amount": 1000}],
    )
    flag = FeatureFlag(
        key="feature.demo",
        name="Demo",
        target_roles=["admin"],
        target_org_ids=["org-1"],
        metadata_={"owner": "qa"},
    )
    conversation = Conversation(context={"intent": "contract"})
    message = Message(
        role=MessageRole.USER,
        content="请审查合同",
        citations=[{"doc_id": "doc-1"}],
        actions=[{"type": "open"}],
        msg_metadata={"source": "chat"},
    )
    case_request = CaseRequest(
        user_id="user-1",
        title="合同纠纷",
        description="服务费拖欠",
        legal_area="contract",
        tags=["合同"],
        extra_data={"amount": 1000},
    )
    user = User(email="u@example.com", ai_profile={"scenario": "contract"})
    document = Document(
        name="服务合同",
        file_path="/tmp/contract.docx",
        ai_analysis={"risk": "low"},
        tags=["合同"],
        doc_metadata={"source": "upload"},
    )
    session = DocumentSession(document_id="doc-1", settings={"mode": "review"})
    collaborator = DocumentCollaborator(
        session_id="session-1",
        cursor_position={"line": 1, "column": 2},
    )
    edit = DocumentEdit(
        session_id="session-1",
        collaborator_id="collab-1",
        operation="insert",
        version=1,
        position={"start": 0, "end": 0},
        format_value={"bold": True},
    )
    case = Case(
        title="案件",
        parties={"plaintiff": "甲"},
        ai_analysis={"risk": "medium"},
    )
    event = CaseEvent(
        case_id="case-1",
        event_type="created",
        title="立案",
        event_data={"stage": "created"},
    )
    audit = AuditLog(
        action="update",
        resource_type="contract",
        old_value={"status": "draft"},
        new_value={"status": "reviewed"},
        extra_data={"request_id": "req-1"},
    )
    approval = Approval(
        title="合同审批",
        requester_id="user-1",
        payload={"contract_id": "contract-1"},
        approval_chain={"mode": "sequential", "steps": []},
    )
    template = ApprovalTemplate(
        name="默认审批",
        created_by="user-1",
        chain_config={"mode": "parallel", "steps": []},
    )

    assert invoice.items == [{"description": "咨询", "amount": 1000}]
    assert flag.target_roles == ["admin"]
    assert conversation.context == {"intent": "contract"}
    assert message.citations == [{"doc_id": "doc-1"}]
    assert case_request.extra_data == {"amount": 1000}
    assert user.ai_profile == {"scenario": "contract"}
    assert document.doc_metadata == {"source": "upload"}
    assert session.settings == {"mode": "review"}
    assert collaborator.cursor_position == {"line": 1, "column": 2}
    assert edit.position == {"start": 0, "end": 0}
    assert case.parties == {"plaintiff": "甲"}
    assert event.event_data == {"stage": "created"}
    assert audit.to_dict()["old_value"] == {"status": "draft"}
    assert approval.payload == {"contract_id": "contract-1"}
    assert template.chain_config == {"mode": "parallel", "steps": []}


def test_more_list_backed_models_accept_typed_payloads():
    task = Task(title="提交材料", tags=["诉讼", "证据"])
    lead = Lead(
        client_name="王客户",
        follow_ups=[{"date": "2026-05-07", "note": "电话沟通"}],
    )
    expert = Expert(
        name="李律师",
        specialty=["公司法"],
        achievements=["年度优秀律师"],
    )
    course = Course(title="合同实务", tags=["合同", "实务"])
    progress = CourseProgress(
        user_id="user-1",
        course_id="course-1",
        completed_lessons=["lesson-1"],
    )

    assert task.tags == ["诉讼", "证据"]
    assert lead.follow_ups == [{"date": "2026-05-07", "note": "电话沟通"}]
    assert expert.specialty == ["公司法"]
    assert expert.achievements == ["年度优秀律师"]
    assert course.tags == ["合同", "实务"]
    assert progress.completed_lessons == ["lesson-1"]
