"""
反馈处理管道 (Feedback Pipeline)
负责收集用户反馈并触发进化流程
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
from pydantic import BaseModel

from src.core.evolution.experience_extractor import ExperienceExtractor
from src.core.memory.episodic_memory import EnhancedEpisodicMemoryService
from src.services.event_bus import event_bus


class UserFeedback(BaseModel):
    """用户反馈模型"""
    episode_id: str
    rating: int  # 1-5 分
    comment: str = ""
    timestamp: datetime = datetime.now()
    session_id: Optional[str] = None
    message_id: Optional[str] = None


class FeedbackPipeline:
    """
    反馈处理管道

    流程:
    1. 接收用户反馈
    2. 更新情景记忆
    3. 触发经验提取
    4. 发布反馈事件
    """

    def __init__(
        self,
        episodic_memory: EnhancedEpisodicMemoryService,
        experience_extractor: ExperienceExtractor
    ):
        self.episodic_memory = episodic_memory
        self.experience_extractor = experience_extractor
        self._feedback_queue: asyncio.Queue[UserFeedback] = asyncio.Queue()
        self._processing = False

    async def start(self):
        """启动反馈处理循环"""
        if self._processing:
            return

        self._processing = True
        logger.info("反馈处理管道已启动")

        asyncio.create_task(self._process_loop())

    async def stop(self):
        """停止反馈处理"""
        self._processing = False
        logger.info("反馈处理管道已停止")

    async def submit_feedback(self, feedback: UserFeedback) -> bool:
        """
        提交用户反馈

        Args:
            feedback: 用户反馈数据

        Returns:
            是否提交成功
        """
        try:
            await self._feedback_queue.put(feedback)

            # 立即更新情景记忆的评分
            await self.episodic_memory.update_feedback(
                episode_id=feedback.episode_id,
                user_rating=feedback.rating,
                user_feedback=feedback.comment
            )

            logger.info(
                f"反馈已提交: {feedback.episode_id}, "
                f"评分: {feedback.rating}"
            )
            return True

        except Exception as e:
            logger.error(f"提交反馈失败: {e}")
            return False

    async def _process_loop(self):
        """反馈处理循环"""
        while self._processing:
            try:
                # 从队列获取反馈 (超时1秒)
                feedback = await asyncio.wait_for(
                    self._feedback_queue.get(),
                    timeout=1.0
                )

                # 处理反馈
                await self._process_feedback(feedback)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"处理反馈异常: {e}")
                await asyncio.sleep(1)

    async def _process_feedback(self, feedback: UserFeedback):
        """
        处理单条反馈

        Args:
            feedback: 用户反馈
        """
        # 1. 验证反馈
        if not self._validate_feedback(feedback):
            logger.warning(f"无效的反馈: {feedback}")
            return

        # 2. 发布反馈事件 (通知其他系统)
        await event_bus.publish("feedback.received", {
            "episode_id": feedback.episode_id,
            "rating": feedback.rating,
            "comment": feedback.comment,
            "timestamp": feedback.timestamp.isoformat()
        })

        # 3. 异步触发经验提取
        if feedback.rating >= 4 or feedback.rating <= 2:
            asyncio.create_task(
                self._trigger_experience_extraction(feedback)
            )

    def _validate_feedback(self, feedback: UserFeedback) -> bool:
        """
        验证反馈数据

        Args:
            feedback: 用户反馈

        Returns:
            是否有效
        """
        if not feedback.episode_id:
            return False

        if feedback.rating < 1 or feedback.rating > 5:
            return False

        return True

    async def _trigger_experience_extraction(self, feedback: UserFeedback):
        """
        触发经验提取

        Args:
            feedback: 用户反馈
        """
        try:
            # 提取经验模式
            patterns = await self.experience_extractor.extract_from_episode(
                episode_id=feedback.episode_id
            )

            if patterns:
                logger.info(
                    f"从反馈 {feedback.episode_id} 提取了 {len(patterns)} 个模式"
                )

                # 发布模式提取事件
                await event_bus.publish("patterns.extracted", {
                    "episode_id": feedback.episode_id,
                    "patterns": [p.dict() for p in patterns],
                    "rating": feedback.rating
                })

        except Exception as e:
            logger.error(f"经验提取失败: {e}")

    async def get_feedback_stats(
        self,
        episode_id: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        获取反馈统计

        Args:
            episode_id: 特定案例 ID (可选)
            limit: 返回数量限制

        Returns:
            统计数据
        """
        # TODO: 实现反馈统计查询
        return {
            "total_feedbacks": 0,
            "average_rating": 0.0,
            "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        }


# 全局实例 (将在主应用中初始化)
feedback_pipeline: Optional[FeedbackPipeline] = None
