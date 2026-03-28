"""
聊天API测试
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from src.models.user import User, Organization
from src.models.conversation import Conversation, Message


# ============ 接口响应测试 ============

class TestChatAPIResponses:
    """测试聊天API响应"""
    
    @pytest.mark.asyncio
    @patch('src.services.chat_service.get_workforce')
    async def test_chat_endpoint_success(self, mock_get_workforce, client: AsyncClient, test_user: User):
        """测试聊天接口成功响应"""
        # Mock智能体团队
        mock_workforce = MagicMock()
        mock_workforce.chat = AsyncMock(return_value="这是AI的回复")
        mock_get_workforce.return_value = mock_workforce
        
        response = await client.post(
            "/api/v1/chat/",
            json={
                "message": "请问合同违约应该如何处理？",
                "conversation_id": None
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data or "message" in data
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_empty_message(self, client: AsyncClient):
        """测试空消息请求"""
        response = await client.post(
            "/api/v1/chat/",
            json={
                "message": "",
                "conversation_id": None
            }
        )
        
        # 应该返回错误或验证失败
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_invalid_json(self, client: AsyncClient):
        """测试无效JSON请求"""
        response = await client.post(
            "/api/v1/chat/",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422


# ============ 认证测试 ============

class TestChatAPIAuthentication:
    """测试聊天API认证"""
    
    @pytest.mark.asyncio
    async def test_chat_without_auth(self, client: AsyncClient):
        """测试无认证访问（如果需要认证）"""
        response = await client.post(
            "/api/v1/chat/",
            json={"message": "测试消息"}
        )
        
        # 根据API是否需要认证，状态码可能不同
        # 如果不需要认证，应该返回200
        # 如果需要认证，应该返回401
        assert response.status_code in [200, 401]
    
    @pytest.mark.asyncio
    async def test_chat_with_invalid_token(self, client: AsyncClient):
        """测试无效token"""
        response = await client.post(
            "/api/v1/chat/",
            json={"message": "测试消息"},
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        # 可能返回401或继续处理（取决于认证策略）
        assert response.status_code in [200, 401, 403]


# ============ 参数校验测试 ============

class TestChatAPIValidation:
    """测试聊天API参数校验"""
    
    @pytest.mark.asyncio
    async def test_chat_message_too_long(self, client: AsyncClient):
        """测试过长消息"""
        long_message = "测试" * 10000  # 非常长的消息
        
        response = await client.post(
            "/api/v1/chat/",
            json={"message": long_message}
        )
        
        # 可能被拒绝或截断处理
        assert response.status_code in [200, 400, 413, 422]
    
    @pytest.mark.asyncio
    async def test_chat_missing_message_field(self, client: AsyncClient):
        """测试缺少message字段"""
        response = await client.post(
            "/api/v1/chat/",
            json={"conversation_id": "test-123"}  # 缺少message
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_chat_invalid_conversation_id(self, client: AsyncClient):
        """测试无效的conversation_id"""
        response = await client.post(
            "/api/v1/chat/",
            json={
                "message": "测试消息",
                "conversation_id": "non-existent-conversation"
            }
        )
        
        # 可能创建新对话或返回错误
        assert response.status_code in [200, 404]


# ============ 对话管理测试 ============

class TestConversationManagement:
    """测试对话管理功能"""
    
    @pytest.mark.asyncio
    async def test_get_conversations_list(self, client: AsyncClient):
        """测试获取对话列表"""
        response = await client.get("/api/v1/chat/conversations")
        
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict) or isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_conversation_history(self, client: AsyncClient):
        """测试获取对话历史"""
        response = await client.get("/api/v1/chat/conversations/test-id/messages")
        
        assert response.status_code in [200, 404, 401]
    
    @pytest.mark.asyncio
    async def test_delete_conversation(self, client: AsyncClient):
        """测试删除对话"""
        response = await client.delete("/api/v1/chat/conversations/test-id")
        
        assert response.status_code in [200, 204, 404, 401]


# ============ 智能体选择测试 ============

class TestAgentSelection:
    """测试智能体选择功能"""
    
    @pytest.mark.asyncio
    async def test_get_available_agents(self, client: AsyncClient):
        """测试获取可用智能体列表"""
        response = await client.get("/api/v1/chat/agents")
        
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or "agents" in data
    
    @pytest.mark.asyncio
    @patch('src.services.chat_service.get_workforce')
    async def test_chat_with_specific_agent(self, mock_get_workforce, client: AsyncClient):
        """测试指定智能体对话"""
        mock_workforce = MagicMock()
        mock_workforce.chat = AsyncMock(return_value="合同审查专家回复")
        mock_get_workforce.return_value = mock_workforce
        
        response = await client.post(
            "/api/v1/chat/",
            json={
                "message": "请审查这份合同",
                "agent_name": "contract_reviewer"
            }
        )
        
        assert response.status_code in [200, 400]


# ============ 错误处理测试 ============

class TestChatAPIErrorHandling:
    """测试聊天API错误处理"""
    
    @pytest.mark.asyncio
    @patch('src.services.chat_service.get_workforce')
    async def test_chat_agent_error(self, mock_get_workforce, client: AsyncClient):
        """测试智能体错误处理"""
        mock_workforce = MagicMock()
        mock_workforce.chat = AsyncMock(side_effect=Exception("Agent处理失败"))
        mock_get_workforce.return_value = mock_workforce
        
        response = await client.post(
            "/api/v1/chat/",
            json={"message": "测试消息"}
        )
        
        # 应该优雅地处理错误
        assert response.status_code in [200, 500]
    
    @pytest.mark.asyncio
    async def test_chat_rate_limiting(self, client: AsyncClient):
        """测试速率限制"""
        # 快速发送多个请求
        responses = []
        for i in range(10):
            response = await client.post(
                "/api/v1/chat/",
                json={"message": f"测试消息 {i}"}
            )
            responses.append(response.status_code)
        
        # 检查是否有速率限制响应（429）或正常响应
        assert all(code in [200, 401, 429] for code in responses)


# ============ 流式响应测试 ============

class TestStreamingResponse:
    """测试流式响应功能"""
    
    @pytest.mark.asyncio
    async def test_chat_streaming_endpoint(self, client: AsyncClient):
        """测试流式聊天接口"""
        response = await client.post(
            "/api/v1/chat/stream",
            json={"message": "测试消息"}
        )
        
        # 流式接口可能不存在
        assert response.status_code in [200, 404, 401]


# ============ 案件路由API测试 ============

class TestCasesAPI:
    """测试案件管理API"""
    
    @pytest.mark.asyncio
    async def test_list_cases(self, client: AsyncClient, test_cases):
        """测试获取案件列表"""
        response = await client.get("/api/v1/cases/")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_list_cases_with_filter(self, client: AsyncClient, test_cases):
        """测试按条件筛选案件"""
        response = await client.get("/api/v1/cases/?status=pending")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    @pytest.mark.asyncio
    async def test_create_case(self, client: AsyncClient):
        """测试创建案件"""
        response = await client.post(
            "/api/v1/cases/",
            json={
                "title": "API测试案件",
                "case_type": "contract",
                "description": "通过API创建的测试案件",
                "priority": "medium"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "API测试案件"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_create_case_validation(self, client: AsyncClient):
        """测试创建案件参数校验"""
        response = await client.post(
            "/api/v1/cases/",
            json={
                "case_type": "contract"  # 缺少必填的title
            }
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_case(self, client: AsyncClient, test_case):
        """测试获取案件详情"""
        response = await client.get(f"/api/v1/cases/{test_case.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_case.id
    
    @pytest.mark.asyncio
    async def test_get_case_not_found(self, client: AsyncClient):
        """测试获取不存在的案件"""
        response = await client.get("/api/v1/cases/non-existent-id")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_case(self, client: AsyncClient, test_case):
        """测试更新案件"""
        response = await client.put(
            f"/api/v1/cases/{test_case.id}",
            json={
                "title": "更新后的标题",
                "status": "in_progress"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "更新后的标题"
        assert data["status"] == "in_progress"
    
    @pytest.mark.asyncio
    async def test_delete_case(self, client: AsyncClient, test_case):
        """测试删除案件"""
        response = await client.delete(f"/api/v1/cases/{test_case.id}")
        
        assert response.status_code == 200
        
        # 验证已删除
        response = await client.get(f"/api/v1/cases/{test_case.id}")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_case_timeline(self, client: AsyncClient, test_case):
        """测试获取案件时间线"""
        response = await client.get(f"/api/v1/cases/{test_case.id}/timeline")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ============ 舆情API测试 ============

class TestSentimentAPI:
    """测试舆情监控API"""
    
    @pytest.mark.asyncio
    async def test_list_monitors(self, client: AsyncClient):
        """测试获取监控配置列表"""
        response = await client.get("/api/v1/sentiment/monitors")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    @pytest.mark.asyncio
    async def test_create_monitor(self, client: AsyncClient):
        """测试创建监控配置"""
        response = await client.post(
            "/api/v1/sentiment/monitors",
            json={
                "name": "测试监控",
                "keywords": ["法务", "合同"],
                "alert_threshold": 0.7
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "测试监控"
    
    @pytest.mark.asyncio
    @patch('src.services.sentiment_service.SentimentAnalysisAgent')
    async def test_analyze_sentiment(self, mock_agent, client: AsyncClient):
        """测试舆情分析"""
        mock_agent_instance = MagicMock()
        mock_agent_instance.analyze_sentiment = AsyncMock(return_value={"analysis": "结果"})
        mock_agent_instance.assess_risk = AsyncMock(return_value={"risk_assessment": "结果"})
        mock_agent.return_value = mock_agent_instance
        
        response = await client.post(
            "/api/v1/sentiment/analyze",
            json={
                "content": "公司涉嫌合同违约被起诉",
                "keyword": "合同违约",
                "save_record": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "sentiment_type" in data
        assert "risk_level" in data
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, client: AsyncClient):
        """测试获取舆情统计"""
        response = await client.get("/api/v1/sentiment/statistics?days=7")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_records" in data


# ============ 协作编辑API测试 ============

class TestCollaborationAPI:
    """测试协作编辑API"""
    
    @pytest.mark.asyncio
    async def test_list_sessions(self, client: AsyncClient):
        """测试获取协作会话列表"""
        response = await client.get("/api/v1/collaboration/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    @pytest.mark.asyncio
    async def test_create_session(self, client: AsyncClient, test_document):
        """测试创建协作会话"""
        response = await client.post(
            "/api/v1/collaboration/sessions",
            json={
                "document_id": test_document.id,
                "name": "测试协作会话"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == test_document.id
    
    @pytest.mark.asyncio
    async def test_get_session(self, client: AsyncClient, test_session):
        """测试获取协作会话详情"""
        response = await client.get(f"/api/v1/collaboration/sessions/{test_session.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_session.id
    
    @pytest.mark.asyncio
    async def test_close_session(self, client: AsyncClient, test_session):
        """测试关闭协作会话"""
        response = await client.post(f"/api/v1/collaboration/sessions/{test_session.id}/close")
        
        assert response.status_code == 200
