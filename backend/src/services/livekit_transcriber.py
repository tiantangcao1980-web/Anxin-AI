"""
LiveKit 实时转录 Agent

作为独立进程运行，自动加入 LiveKit 房间进行语音转录。
转录结果通过两条通道推送：
1. LiveKit 内置 text stream → 前端实时字幕
2. meeting_assistant.on_message() → 复用 Phase 1 AI 分析管道

启动：
  cd backend && python -m src.services.livekit_transcriber console

环境变量：
  LIVEKIT_URL=ws://localhost:7880
  LIVEKIT_API_KEY=anxin_livekit_key
  LIVEKIT_API_SECRET=<secret>
  DASHSCOPE_API_KEY=<阿里云百炼 API Key>  (用于 Paraformer ASR)
"""

import asyncio
import os
import sys
from collections.abc import Awaitable, Callable
from typing import Any, cast

from dotenv import load_dotenv
from loguru import logger

# 确保项目根目录在 sys.path 中（独立进程运行时需要）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv()


def create_agent_server() -> Any:
    """创建 LiveKit Agent 服务器"""
    try:
        from livekit.agents import Agent, AgentServer, AgentSession, JobContext
    except ImportError:
        logger.error(
            "LiveKit Agents 未安装，请执行:\n"
            "  pip install livekit-agents livekit-plugins-aliyun"
        )
        sys.exit(1)

    # 选择 STT 引擎
    stt_engine = _get_stt_engine()
    if not stt_engine:
        logger.error("无可用的 STT 引擎")
        sys.exit(1)

    server = AgentServer()
    rtc_session = cast(
        Callable[[Callable[[JobContext], Awaitable[None]]], Callable[[JobContext], Awaitable[None]]],
        server.rtc_session(agent_name="anxin-transcriber"),
    )

    @rtc_session
    async def entrypoint(ctx: JobContext) -> None:
        """转录 Agent 入口"""
        room_name = ctx.room.name
        logger.info(f"转录 Agent 加入房间: {room_name}")

        session = AgentSession(stt=stt_engine)
        transcript_handler = cast(
            Callable[[Callable[[Any], None]], Callable[[Any], None]],
            session.on("user_input_transcribed"),
        )

        @transcript_handler
        def on_transcript(transcript: Any) -> None:
            """收到转录结果"""
            if not transcript.is_final:
                return

            text = transcript.transcript.strip()
            if not text:
                return

            logger.info(f"[转录] {room_name}: {text[:80]}...")

            # 推送到 AI 旁听管道（异步，不阻塞转录流）
            # 从房间名解析 conversation_id（格式：call_{conv_id}_{timestamp}）
            parts = room_name.split("_", 2)
            if len(parts) >= 2:
                conv_id = parts[1]
                asyncio.create_task(_push_to_assistant(conv_id, text))

        await session.start(
            agent=Agent(instructions="Transcribe all speech in the room."),
            room=ctx.room,
        )
        await ctx.connect()

    return server


def _get_stt_engine() -> Any | None:
    """获取 STT 引擎（优先阿里云 Paraformer）"""
    # 优先阿里云 Paraformer
    if os.environ.get("DASHSCOPE_API_KEY"):
        try:
            from livekit.plugins import aliyun
            logger.info("使用阿里云百炼 Paraformer 实时 ASR")
            return aliyun.STT(model="paraformer-realtime-v2")
        except ImportError:
            logger.warning("livekit-plugins-aliyun 未安装")

    # 回退到 Deepgram
    if os.environ.get("DEEPGRAM_API_KEY"):
        try:
            from livekit.agents import inference
            logger.info("使用 Deepgram ASR")
            return inference.STT(model="deepgram/nova-3-general")
        except ImportError:
            pass

    logger.warning("未配置 ASR 引擎（需要 DASHSCOPE_API_KEY 或 DEEPGRAM_API_KEY）")
    return None


async def _push_to_assistant(conversation_id: str, text: str) -> None:
    """将转录文本推送到 AI 旁听助手"""
    try:
        from src.services.meeting_assistant_service import meeting_assistant
        await meeting_assistant.on_message(
            conversation_id=conversation_id,
            sender_id="voice_participant",
            content=text,
            sender_name="语音",
        )
    except Exception as e:
        logger.error(f"推送转录到 AI 助手失败: {e}")


if __name__ == "__main__":
    from livekit.agents import cli
    server = create_agent_server()
    cli.run_app(server)
