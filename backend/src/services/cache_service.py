"""
增强缓存服务 (Enhanced Cache Service)
三层缓存架构: L1(内存) -> L2(Redis) -> L3(数据库)
提供缓存操作和缓存装饰器
"""

import json
import hashlib
import functools
from typing import Optional, Any, Callable, TypeVar, Union, Dict, List
from datetime import datetime, timedelta
from collections import OrderedDict

import redis.asyncio as redis
from loguru import logger

from src.core.config import settings


# 类型变量用于装饰器
T = TypeVar('T')


class CacheEntry:
    """L1 内存缓存条目"""
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.expires_at = datetime.now() + timedelta(seconds=ttl)

    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.now() > self.expires_at


class CacheService:
    """
    三层缓存服务
    - L1: 内存缓存 (最快, 5秒TTL)
    - L2: Redis缓存 (中速, 1小时TTL)
    - L3: 数据库 (持久化, 无TTL)
    """

    # 缓存层级配置
    L1_TTL = 5  # 秒
    L2_TTL = 3600  # 1小时
    DEFAULT_TTL = 3600  # 默认1小时

    # L1 内存缓存配置
    L1_MAX_SIZE = 100  # 最大条目数

    # 缓存Key前缀
    KEY_PREFIX = "legal_agent"

    def __init__(
        self,
        enable_l1: bool = True,
        enable_l2: bool = True
    ):
        self._client: Optional[redis.Redis] = None

        # L1: 内存缓存 (有序字典,自动淘汰旧数据)
        self.enable_l1 = enable_l1
        self._l1_cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # L2: Redis 开关
        self.enable_l2 = enable_l2

        # 统计信息
        self._stats = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "l3_misses": 0,
        }
    
    def _cleanup_expired_l1(self):
        """清理过期的 L1 缓存"""
        now = datetime.now()
        expired_keys = [
            k for k, v in self._l1_cache.items()
            if v.is_expired()
        ]
        for key in expired_keys:
            del self._l1_cache[key]

    def _enforce_l1_size_limit(self):
        """强制执行 L1 大小限制"""
        self._cleanup_expired_l1()

        # 如果仍然超过大小限制,删除最旧的条目
        while len(self._l1_cache) > self.L1_MAX_SIZE:
            self._l1_cache.popitem(last=False)

    async def get_client(self) -> redis.Redis:
        """获取Redis客户端（懒加载）"""
        if self._client is None:
            self._client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client
    
    def _make_key(self, module: str, resource: str, id: str = "") -> str:
        """
        生成缓存Key
        格式：{前缀}:{模块}:{资源}:{ID}
        
        Args:
            module: 模块名称（如 user, case, search）
            resource: 资源类型（如 info, list, detail）
            id: 资源ID（可选）
        
        Returns:
            格式化的缓存Key
        """
        if id:
            return f"{self.KEY_PREFIX}:{module}:{resource}:{id}"
        return f"{self.KEY_PREFIX}:{module}:{resource}"
    
    async def get(
        self,
        key: str,
        l3_loader: Optional[Callable] = None
    ) -> Optional[Any]:
        """
        获取缓存值 (三层查找)

        Args:
            key: 缓存Key
            l3_loader: L3 数据加载函数 (当 L1/L2 都未命中时调用)

        Returns:
            缓存值，不存在返回None
        """
        if l3_loader is not None and not callable(l3_loader):
            key = self._make_key(key, str(l3_loader))
            l3_loader = None

        # L1: 内存缓存查找
        if self.enable_l1:
            entry = self._l1_cache.get(key)
            if entry and not entry.is_expired():
                self._stats["l1_hits"] += 1
                logger.debug(f"L1缓存命中: {key}")
                return entry.value
            self._stats["l1_misses"] += 1

        # L2: Redis 缓存查找
        if self.enable_l2:
            try:
                client = await self.get_client()
                value = await client.get(key)
                if value:
                    self._stats["l2_hits"] += 1
                    logger.debug(f"L2缓存命中: {key}")

                    try:
                        parsed_value = json.loads(value)
                    except json.JSONDecodeError:
                        parsed_value = value

                    # 回写 L1
                    if self.enable_l1:
                        self._l1_cache[key] = CacheEntry(parsed_value, self.L1_TTL)
                        self._enforce_l1_size_limit()

                    return parsed_value
                self._stats["l2_misses"] += 1
            except Exception as e:
                logger.warning(f"L2缓存读取失败 key={key}: {e}")

        # L3: 数据库加载
        self._stats["l3_misses"] += 1
        if l3_loader:
            value = await l3_loader()

            # 回写 L1 和 L2
            if value is not None:
                await self.set(key, value)

            return value

        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        data: Any = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        设置缓存值 (同时写入 L1 和 L2)

        Args:
            key: 缓存Key
            value: 缓存值（会自动JSON序列化）
            ttl: 过期时间（秒），默认1小时

        Returns:
            是否设置成功
        """
        if data is not None:
            key = self._make_key(key, str(value))
            value = data

        success = True

        # L1: 写入内存缓存
        if self.enable_l1:
            l1_ttl = ttl or self.L1_TTL
            self._l1_cache[key] = CacheEntry(value, l1_ttl)
            self._enforce_l1_size_limit()

        # L2: 写入 Redis
        if self.enable_l2:
            try:
                client = await self.get_client()
                # JSON序列化
                if isinstance(value, (dict, list)):
                    serialized = json.dumps(value, ensure_ascii=False, default=str)
                elif not isinstance(value, str):
                    serialized = json.dumps(value, ensure_ascii=False, default=str)
                else:
                    serialized = value

                expire = ttl if ttl is not None else self.DEFAULT_TTL
                await client.set(key, serialized, ex=expire)
                logger.debug(f"L2缓存写入: {key}")
            except Exception as e:
                logger.warning(f"L2缓存写入失败 key={key}: {e}")
                success = False

        return success
    
    async def delete(self, key: str) -> bool:
        """
        删除缓存 (同时删除 L1 和 L2)

        Args:
            key: 缓存Key

        Returns:
            是否删除成功
        """
        success = True

        # 从 L1 删除
        if self.enable_l1 and key in self._l1_cache:
            del self._l1_cache[key]

        # 从 L2 删除
        if self.enable_l2:
            try:
                client = await self.get_client()
                await client.delete(key)
                logger.debug(f"L2缓存删除: {key}")
            except Exception as e:
                logger.warning(f"L2缓存删除失败 key={key}: {e}")
                success = False

        return success
    
    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在
        
        Args:
            key: 缓存Key
            
        Returns:
            是否存在
        """
        try:
            client = await self.get_client()
            return bool(await client.exists(key))
        except Exception as e:
            logger.warning(f"检查缓存存在失败 key={key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的所有Key
        
        Args:
            pattern: Key模式（如 legal_agent:user:*）
            
        Returns:
            删除的Key数量
        """
        try:
            client = await self.get_client()
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await client.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.warning(f"批量删除缓存失败 pattern={pattern}: {e}")
            return 0
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """
        增加计数器
        
        Args:
            key: 缓存Key
            amount: 增加量
            
        Returns:
            增加后的值
        """
        try:
            client = await self.get_client()
            return await client.incrby(key, amount)
        except Exception as e:
            logger.warning(f"增加计数器失败 key={key}: {e}")
            return 0
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        设置Key过期时间
        
        Args:
            key: 缓存Key
            ttl: 过期时间（秒）
            
        Returns:
            是否设置成功
        """
        try:
            client = await self.get_client()
            return await client.expire(key, ttl)
        except Exception as e:
            logger.warning(f"设置过期时间失败 key={key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """
        获取Key剩余过期时间
        
        Args:
            key: 缓存Key
            
        Returns:
            剩余秒数，-1表示永不过期，-2表示不存在
        """
        try:
            client = await self.get_client()
            return await client.ttl(key)
        except Exception as e:
            logger.warning(f"获取TTL失败 key={key}: {e}")
            return -2
    
    # ========== 用户缓存 ==========
    
    async def get_user(self, user_id: str) -> Optional[dict]:
        """获取用户信息缓存"""
        key = self._make_key("user", "info", user_id)
        return await self.get(key)
    
    async def set_user(self, user_id: str, user_data: dict, ttl: int = 1800) -> bool:
        """设置用户信息缓存（默认30分钟）"""
        key = self._make_key("user", "info", user_id)
        return await self.set(key, user_data, ttl)
    
    async def invalidate_user(self, user_id: str) -> bool:
        """失效用户缓存"""
        key = self._make_key("user", "info", user_id)
        return await self.delete(key)
    
    # ========== 案件缓存 ==========
    
    async def get_case(self, case_id: str) -> Optional[dict]:
        """获取案件详情缓存"""
        key = self._make_key("case", "detail", case_id)
        return await self.get(key)
    
    async def set_case(self, case_id: str, case_data: dict, ttl: int = 600) -> bool:
        """设置案件详情缓存（默认10分钟）"""
        key = self._make_key("case", "detail", case_id)
        return await self.set(key, case_data, ttl)
    
    async def invalidate_case(self, case_id: str) -> bool:
        """失效案件缓存"""
        key = self._make_key("case", "detail", case_id)
        return await self.delete(key)
    
    async def get_case_list(self, user_id: str, page: int = 1) -> Optional[dict]:
        """获取案件列表缓存"""
        key = self._make_key("case", "list", f"{user_id}:{page}")
        return await self.get(key)
    
    async def set_case_list(
        self, user_id: str, page: int, data: dict, ttl: int = 300
    ) -> bool:
        """设置案件列表缓存（默认5分钟）"""
        key = self._make_key("case", "list", f"{user_id}:{page}")
        return await self.set(key, data, ttl)
    
    async def invalidate_case_list(self, user_id: str) -> int:
        """失效用户的所有案件列表缓存"""
        pattern = f"{self.KEY_PREFIX}:case:list:{user_id}:*"
        return await self.delete_pattern(pattern)
    
    # ========== 搜索结果缓存 ==========
    
    async def get_search_result(self, query_hash: str) -> Optional[dict]:
        """获取搜索结果缓存"""
        key = self._make_key("search", "result", query_hash)
        return await self.get(key)
    
    async def set_search_result(
        self, query_hash: str, result: dict, ttl: int = 1800
    ) -> bool:
        """设置搜索结果缓存（默认30分钟）"""
        key = self._make_key("search", "result", query_hash)
        return await self.set(key, result, ttl)
    
    @staticmethod
    def hash_query(query: str, **kwargs) -> str:
        """生成查询参数的哈希值"""
        params = {"query": query, **kwargs}
        param_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(param_str.encode()).hexdigest()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_hits = (
            self._stats["l1_hits"] +
            self._stats["l2_hits"]
        )
        total_misses = (
            self._stats["l1_misses"] +
            self._stats["l2_misses"] +
            self._stats["l3_misses"]
        )
        total_requests = total_hits + total_misses

        hit_rate = total_hits / total_requests if total_requests > 0 else 0

        return {
            "l1_enabled": self.enable_l1,
            "l2_enabled": self.enable_l2,
            "l1_size": len(self._l1_cache),
            "l1_max_size": self.L1_MAX_SIZE,
            "stats": self._stats,
            "hit_rate": f"{hit_rate * 100:.2f}%",
            "total_requests": total_requests,
        }

    async def clear_l1(self):
        """清空 L1 缓存"""
        self._l1_cache.clear()
        logger.info("L1 缓存已清空")

    async def clear_l2(self):
        """清空 L2 缓存"""
        if self.enable_l2 and self._client:
            try:
                await self._client.flushdb()
                logger.info("L2 缓存已清空")
            except Exception as e:
                logger.warning(f"清空 L2 缓存失败: {e}")

    async def warm_up(
        self,
        data: List[Dict[str, Any]],
        prefix: str,
        id_field: str = "id"
    ):
        """
        缓存预热
        :param data: 预热数据列表
        :param prefix: 键前缀
        :param id_field: ID 字段名
        """
        logger.info(f"🔥 开始缓存预热: {len(data)} 条数据")

        for item in data:
            item_id = item.get(id_field)
            if item_id:
                key = self._make_key(prefix, "info", str(item_id))
                await self.set(key, item, ttl=self.L2_TTL)

        logger.info(f"✅ 缓存预热完成")

    async def close(self):
        """关闭Redis连接"""
        if self._client:
            await self._client.close()
            self._client = None


# 全局缓存服务实例
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """获取缓存服务单例"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


# ========== 缓存装饰器 ==========


def cached(
    module: str,
    resource: str,
    ttl: int = 3600,
    key_builder: Optional[Callable[..., str]] = None,
):
    """
    缓存装饰器
    
    用于装饰异步函数，自动处理缓存的读取和写入
    
    Args:
        module: 模块名称
        resource: 资源类型
        ttl: 缓存过期时间（秒）
        key_builder: 自定义Key生成函数，接收函数参数，返回Key后缀
        
    Example:
        @cached(module="user", resource="info", ttl=1800)
        async def get_user_info(user_id: str) -> dict:
            ...
            
        @cached(module="case", resource="list", key_builder=lambda user_id, page: f"{user_id}:{page}")
        async def list_cases(user_id: str, page: int = 1) -> dict:
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            cache = get_cache_service()
            
            # 生成缓存Key
            if key_builder:
                key_suffix = key_builder(*args, **kwargs)
            else:
                # 默认使用第一个位置参数或id/user_id关键字参数
                if args:
                    key_suffix = str(args[0])
                elif "id" in kwargs:
                    key_suffix = str(kwargs["id"])
                elif "user_id" in kwargs:
                    key_suffix = str(kwargs["user_id"])
                else:
                    # 使用所有参数的哈希
                    key_suffix = CacheService.hash_query(
                        func.__name__, args=str(args), kwargs=str(kwargs)
                    )
            
            cache_key = cache._make_key(module, resource, key_suffix)
            
            # 尝试从缓存获取
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_value
            
            # 执行原函数
            result = await func(*args, **kwargs)
            
            # 写入缓存
            if result is not None:
                await cache.set(cache_key, result, ttl)
                logger.debug(f"缓存写入: {cache_key}")
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(module: str, resource: str, key_suffix: str = "*"):
    """
    缓存失效装饰器
    
    用于装饰会修改数据的函数，自动失效相关缓存
    
    Args:
        module: 模块名称
        resource: 资源类型
        key_suffix: Key后缀，支持 * 通配符
        
    Example:
        @invalidate_cache(module="user", resource="info")
        async def update_user(user_id: str, data: dict) -> dict:
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # 先执行原函数
            result = await func(*args, **kwargs)
            
            # 失效缓存
            cache = get_cache_service()
            
            # 确定要失效的Key后缀
            suffix = key_suffix
            if suffix == "*" and args:
                suffix = str(args[0])
            elif suffix == "*" and "id" in kwargs:
                suffix = str(kwargs["id"])
            
            if "*" in suffix:
                pattern = f"{cache.KEY_PREFIX}:{module}:{resource}:{suffix}"
                await cache.delete_pattern(pattern)
            else:
                cache_key = cache._make_key(module, resource, suffix)
                await cache.delete(cache_key)
            
            return result
        
        return wrapper
    return decorator
