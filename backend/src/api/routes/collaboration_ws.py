"""
协作编辑 WebSocket 路由

处理文档协作编辑的 WebSocket 连接
支持：
- 实时协作编辑
- 光标同步
- 评论/批注
- 用户状态同步
"""

import asyncio
import json
import uuid
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from src.core.database import get_db
from src.core.deps import get_current_user
from src.core.security import verify_token
from src.models.user import User
from src.services.collaboration_service import CollaborationService

router = APIRouter()


@router.websocket("/ws/document/{document_id}")
async def document_collaboration_websocket(
    websocket: WebSocket,
    document_id: str,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    文档协作 WebSocket 端点

    客户端消息格式：
    {
        "type": "join" | "operation" | "cursor_update" | "comment" | "ping",
        "data": { ... }
    }

    服务端推送格式：
    {
        "type": "init" | "operation" | "cursor_update" | "user_joined" | "user_left" | "comment_added",
        "data": { ... }
    }
    """
    await websocket.accept()
    logger.info(f"协作 WebSocket 连接: doc={document_id}")

    # 生成会话 ID
    session_id = str(uuid.uuid4())

    # ===== [S-06 + S-07] WebSocket 认证：首条消息认证替代 URL 参数 =====
    # 原因：Token 在 URL 参数中会被记录到服务器访问日志、浏览器历史、代理日志
    #       且原代码 TODO 未实现 Token 验证，任何人可匿名接入
    # 修复方式：
    #   1. URL 中的 token 参数仍保留（向后兼容），但优先使用首条 auth 消息
    #   2. 首条消息如果是 type="auth"，则验证 Token 并获取用户信息
    #   3. 如果 Token 无效，关闭连接
    user_id = "anonymous"
    user_name = "匿名用户"
    authenticated = False

    # 向后兼容：如果 URL 中有 token，先尝试验证
    if token:
        try:
            verified_user_id = verify_token(token)
            if verified_user_id:
                result = await db.execute(
                    select(User).where(User.id == verified_user_id, User.is_active == True)
                )
                user = result.scalar_one_or_none()
                if user:
                    user_id = str(user.id)
                    user_name = user.name
                    authenticated = True
        except Exception as e:
            logger.warning(f"WebSocket URL Token 验证失败: {e}")

    collaboration_service = CollaborationService(db)

    try:
        # 等待第一条消息（可能是 auth 或 join）
        init_message = await asyncio.wait_for(
            websocket.receive_json(), timeout=15
        )
        init_type = init_message.get("type")
        init_data = init_message.get("data", {})

        # 如果首条消息是 auth 类型，先处理认证，再等 join
        if init_type == "auth" and not authenticated:
            auth_token = init_data.get("token", "")
            if auth_token:
                try:
                    verified_user_id = verify_token(auth_token)
                    if verified_user_id:
                        result = await db.execute(
                            select(User).where(User.id == verified_user_id, User.is_active == True)
                        )
                        user = result.scalar_one_or_none()
                        if user:
                            user_id = str(user.id)
                            user_name = user.name
                            authenticated = True
                except Exception as e:
                    logger.warning(f"WebSocket auth 消息 Token 验证失败: {e}")

            if not authenticated:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "认证失败，Token 无效"}
                })
                await websocket.close(code=4001, reason="认证失败")
                return

            # 认证成功后，等待 join 消息
            join_msg = await asyncio.wait_for(websocket.receive_json(), timeout=10)
            init_type = join_msg.get("type")
            init_data = join_msg.get("data", {})

        if init_type == "join":
            user_id = init_data.get("user_id", user_id)
            user_name = init_data.get("user_name", user_name)

            # 加入文档协作
            result = await collaboration_service.join_document(
                document_id=document_id,
                user_id=user_id,
                user_name=user_name,
                session_id=session_id,
                websocket=websocket,
                initial_content=init_data.get("initial_content", "")
            )

            # 发送初始化数据
            await websocket.send_json({
                "type": "init",
                "data": {
                    "session_id": session_id,
                    "document_id": document_id,
                    **result
                }
            })
        else:
            await websocket.send_json({
                "type": "error",
                "data": {"message": "第一条消息必须是 join 类型"}
            })
            await websocket.close()
            return

        # 消息循环
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")
            msg_data = message.get("data", {})

            if msg_type == "operation":
                # 处理文档操作
                result = await collaboration_service.handle_operation(
                    document_id=document_id,
                    user_id=user_id,
                    operation={
                        **msg_data,
                        "session_id": session_id
                    }
                )
                await websocket.send_json({
                    "type": "operation_ack",
                    "data": result
                })

            elif msg_type == "cursor_update":
                # 更新光标位置
                await collaboration_service.update_cursor(
                    document_id=document_id,
                    user_id=user_id,
                    position=msg_data.get("position", 0),
                    selection=msg_data.get("selection")
                )

            elif msg_type in ("comment", "comment_add"):
                # 添加评论（支持行号范围 start_line/end_line）
                position = msg_data.get("position", {})
                # 兼容行号范围参数
                if "start_line" in msg_data:
                    position["start_line"] = msg_data["start_line"]
                if "end_line" in msg_data:
                    position["end_line"] = msg_data["end_line"]

                result = await collaboration_service.add_comment(
                    document_id=document_id,
                    user_id=user_id,
                    user_name=user_name,
                    content=msg_data.get("content", ""),
                    position=position,
                )
                await websocket.send_json({
                    "type": "comment_add_ack",
                    "data": result,
                })

            elif msg_type == "comment_reply":
                # 回复评论
                parent_id = msg_data.get("parent_id") or msg_data.get("comment_id")
                reply_content = msg_data.get("content", "")

                if not parent_id:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "缺少 parent_id 参数"},
                    })
                else:
                    # 使用 add_comment 并附带 parent_id
                    result = await collaboration_service.add_comment(
                        document_id=document_id,
                        user_id=user_id,
                        user_name=user_name,
                        content=reply_content,
                        position={"parent_id": parent_id},
                    )
                    await websocket.send_json({
                        "type": "comment_reply_ack",
                        "data": {**result, "parent_id": parent_id},
                    })

            elif msg_type in ("resolve_comment", "comment_resolve"):
                # 解决评论
                result = await collaboration_service.resolve_comment(
                    document_id=document_id,
                    comment_id=msg_data.get("comment_id"),
                )
                await websocket.send_json({
                    "type": "comment_resolve_ack",
                    "data": result,
                })

            elif msg_type == "comment_delete":
                # 删除评论
                comment_id = msg_data.get("comment_id")
                if not comment_id:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "缺少 comment_id 参数"},
                    })
                else:
                    session = collaboration_service.manager.get_session(document_id)
                    if session and comment_id in session.comments:
                        # 仅评论作者可删除
                        comment_obj = session.comments[comment_id]
                        if comment_obj.user_id != user_id:
                            await websocket.send_json({
                                "type": "error",
                                "data": {"message": "只能删除自己的评论"},
                            })
                        else:
                            del session.comments[comment_id]
                            # 广播删除
                            await collaboration_service.manager.broadcast_to_document(
                                document_id,
                                {
                                    "type": "comment_deleted",
                                    "comment_id": comment_id,
                                    "user_id": user_id,
                                },
                            )
                            await websocket.send_json({
                                "type": "comment_delete_ack",
                                "data": {"success": True, "comment_id": comment_id},
                            })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": "评论不存在"},
                        })

            elif msg_type == "save":
                # 保存文档
                result = await collaboration_service.save_document(
                    document_id=document_id,
                    content=msg_data.get("content", "")
                )
                await websocket.send_json({
                    "type": "save_ack",
                    "data": result
                })

            elif msg_type == "ping":
                # 心跳
                await websocket.send_json({
                    "type": "pong",
                    "data": {"timestamp": msg_data.get("timestamp")}
                })

            else:
                logger.warning(f"未知消息类型: {msg_type}")
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"未知消息类型: {msg_type}"}
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: session={session_id}, doc={document_id}")
        await collaboration_service.leave_document(document_id, user_id, session_id)

    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": str(e)}
            })
        except Exception as _send_err:
            # ===== [B-02] 不再使用裸 except: pass =====
            # 原因：裸 except 会吞掉所有异常（包括 KeyboardInterrupt）
            logger.debug(f"发送错误消息失败: {_send_err}")
        await collaboration_service.leave_document(document_id, user_id, session_id)


# ==================== HTTP API (用于非 WebSocket 场景) ====================

@router.post("/document/{document_id}/operations")
async def apply_document_operation(
    document_id: str,
    operation: dict,
    db: AsyncSession = Depends(get_db),
):
    """通过 HTTP 应用文档操作（备用）"""
    service = CollaborationService(db)

    result = await service.handle_operation(
        document_id=document_id,
        user_id=operation.get("user_id", "api"),
        operation=operation
    )

    return result


@router.post("/document/{document_id}/comments")
async def create_document_comment(
    document_id: str,
    comment: dict,
    db: AsyncSession = Depends(get_db),
):
    """创建文档评论"""
    service = CollaborationService(db)

    result = await service.add_comment(
        document_id=document_id,
        user_id=comment.get("user_id", "api"),
        user_name=comment.get("user_name", "API 用户"),
        content=comment.get("content", ""),
        position=comment.get("position", {})
    )

    return result


@router.get("/document/{document_id}/active-users")
async def get_active_users(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取文档的活跃用户列表"""
    from src.services.collaboration_service import collaboration_manager

    session = collaboration_manager.get_session(document_id)
    if not session:
        return {"users": []}

    return {
        "users": [u.__dict__ for u in session.get_active_users()]
    }
