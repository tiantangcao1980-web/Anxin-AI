# -*- coding: utf-8 -*-
"""
事件总线服务 (Event Bus Service)
基于 Redis 实现的轻量级事件分发系统
用于实现 Agent 之间的异步通信和解耦
"""

import json
import asyncio
from typing import Dict, Any, Callable, Awaitable, List
from loguru import logger
import redis.asyncio as redis
from src.core.config import settings


class EventBus:
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.redis: redis.Redis = None
        self.subscribers: Dict[str, List[Callable[[Dict[str, Any]], Awaitable[None]]]] = {}
        self.is_connected = False
        self._pubsub = None
        self._listen_task = None

    async def connect(self):
        """连接到 Redis（仅建立连接，不启动监听循环）"""
        if self.is_connected:
            return

        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            self.is_connected = True
            self._pubsub = self.redis.pubsub()
            logger.info(f"EventBus 已连接到 Redis: {self.redis_url}")
        except Exception as e:
            logger.error(f"EventBus 连接失败: {e}")
            self.is_connected = False

    async def disconnect(self):
        """断开连接"""
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None

        if self.redis:
            await self.redis.close()
            self.redis = None

        self.is_connected = False
        logger.info("EventBus 已断开连接")

    async def publish(self, channel: str, message: Dict[str, Any]):
        """发布事件"""
        if not self.is_connected:
            await self.connect()

        try:
            if "timestamp" not in message:
                import time
                message["timestamp"] = time.time()

            payload = json.dumps(message, ensure_ascii=False)
            await self.redis.publish(channel, payload)
            logger.debug(f"EventBus 发布消息到 [{channel}]: {payload[:100]}...")
        except Exception as e:
            logger.error(f"EventBus 发布失败: {e}")

    async def subscribe(self, channel: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """订阅频道"""
        if not self.is_connected:
            await self.connect()

        if channel not in self.subscribers:
            self.subscribers[channel] = []
            if self._pubsub:
                await self._pubsub.subscribe(channel)
                logger.info(f"EventBus Redis 订阅频道: [{channel}]")

        self.subscribers[channel].append(callback)
        logger.info(f"EventBus 新增订阅者: [{channel}]")

        # 首次有订阅后才启动监听循环
        if self._listen_task is None and self._pubsub:
            self._listen_task = asyncio.create_task(self._listen_loop())
            logger.info("EventBus 监听循环已启动")

    async def _listen_loop(self):
        """监听循环（仅在至少有一个 subscribe 后才会被启动）"""
        while True:
            try:
                if not self.is_connected or not self._pubsub:
                    await asyncio.sleep(1)
                    continue

                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]

                    try:
                        payload = json.loads(data)
                        if channel in self.subscribers:
                            tasks = [cb(payload) for cb in self.subscribers[channel]]
                            if tasks:
                                await asyncio.gather(*tasks, return_exceptions=True)
                    except json.JSONDecodeError:
                        logger.warning(f"EventBus 收到非 JSON 消息: {data}")
                    except Exception as e:
                        logger.error(f"EventBus 处理消息异常: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"EventBus 监听循环异常: {e}")
                await asyncio.sleep(1)


# 全局单例
event_bus = EventBus()
