# -*- coding: utf-8 -*-
"""
采集器抽象基类

提供统一的下载、解析、幂等检查、重试、限速、进度报告等基础设施。
所有具体采集器继承此类，只需实现 download() 和 parse() 方法。
"""

import asyncio
import hashlib
import json
import os
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger


# ==================== 数据结构 ====================


@dataclass
class ParsedDocument:
    """标准化的解析后文档，所有采集器输出此格式"""

    doc_id: str  # 稳定标识符，如 "civil_code_art_496"
    title: str
    content: str
    source: str  # 来源网站名称
    source_url: str  # 原始URL
    knowledge_type: str  # KnowledgeType value: law/regulation/template/...
    law_category: str = ""  # 法律分类
    effective_date: str = ""  # 生效日期
    issuing_authority: str = ""  # 发布机关
    tags: List[str] = field(default_factory=list)
    cross_references: List[str] = field(default_factory=list)  # 交叉引用
    content_hash: str = ""  # SHA256
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.content_hash and self.content:
            self.content_hash = hashlib.sha256(
                self.content.encode("utf-8")
            ).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CollectorManifest:
    """采集器同步状态清单，用于增量更新"""

    source_name: str
    last_sync_at: str = ""  # ISO格式时间戳
    last_sync_hash: str = ""  # 最后下载文件的SHA256
    total_documents: int = 0
    document_hashes: Dict[str, str] = field(default_factory=dict)  # doc_id → content_hash
    version: str = "1.0"
    errors: List[str] = field(default_factory=list)


@dataclass
class CollectorResult:
    """采集结果"""

    source_name: str
    success: bool
    total_downloaded: int = 0
    total_parsed: int = 0
    total_new: int = 0
    total_updated: int = 0
    total_skipped: int = 0
    errors: List[str] = field(default_factory=list)
    documents: List[ParsedDocument] = field(default_factory=list)
    duration_seconds: float = 0.0


# ==================== 基类 ====================


class BaseCollector(ABC):
    """采集器抽象基类"""

    source_name: str = ""  # 子类必须定义
    knowledge_type: str = "other"  # 默认知识类型

    # 配置（可被子类或运行时覆盖）
    rate_limit: float = 2.0  # 请求间隔(秒)
    max_retries: int = 3
    request_timeout: int = 30

    # 常用 User-Agent 列表
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    ]

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw" / self.source_name
        self.processed_dir = self.data_dir / "processed" / self.source_name
        self.manifest_path = self.data_dir / "manifests" / f"{self.source_name}.json"
        self.log_path = self.data_dir / "logs" / f"{self.source_name}.log"

        # 确保目录存在
        for d in [self.raw_dir, self.processed_dir, self.manifest_path.parent]:
            d.mkdir(parents=True, exist_ok=True)

        self._client: Optional[httpx.AsyncClient] = None
        self._manifest: Optional[CollectorManifest] = None
        self._progress_callback = None

    # ==================== 抽象方法 ====================

    @abstractmethod
    async def download(self) -> List[Path]:
        """
        下载原始数据文件到 self.raw_dir。
        返回下载的文件路径列表。
        """
        ...

    @abstractmethod
    async def parse(self, downloaded_files: List[Path]) -> List[ParsedDocument]:
        """
        解析下载的文件，返回标准化的 ParsedDocument 列表。
        """
        ...

    # ==================== 主流程 ====================

    async def collect(
        self, force: bool = False, progress_callback=None
    ) -> CollectorResult:
        """
        完整采集流程：下载 → 解析 → 增量检查

        Args:
            force: 强制重新下载，忽略manifest
            progress_callback: 进度回调 (stage, message, progress_pct)
        """
        self._progress_callback = progress_callback
        start_time = time.time()
        result = CollectorResult(source_name=self.source_name, success=False)

        try:
            self._report_progress("download", f"开始采集 {self.source_name}", 0)

            # 1. 下载
            self._report_progress("download", "正在下载原始数据...", 10)
            downloaded = await self.download()
            result.total_downloaded = len(downloaded)

            if not downloaded:
                result.errors.append("未下载到任何文件")
                return result

            self._report_progress("parse", "正在解析数据...", 40)

            # 2. 解析
            documents = await self.parse(downloaded)
            result.total_parsed = len(documents)

            if not documents:
                result.errors.append("未解析到任何文档")
                return result

            self._report_progress("check", "正在执行增量检查...", 70)

            # 3. 增量检查
            manifest = self._load_manifest()
            new_docs = []
            for doc in documents:
                old_hash = manifest.document_hashes.get(doc.doc_id)
                if old_hash is None:
                    result.total_new += 1
                    new_docs.append(doc)
                elif old_hash != doc.content_hash:
                    result.total_updated += 1
                    new_docs.append(doc)
                else:
                    if not force:
                        result.total_skipped += 1
                    else:
                        new_docs.append(doc)

            result.documents = new_docs if not force else documents

            # 4. 更新 manifest
            for doc in documents:
                manifest.document_hashes[doc.doc_id] = doc.content_hash
            manifest.total_documents = len(manifest.document_hashes)
            manifest.last_sync_at = datetime.now().isoformat()
            manifest.errors = result.errors
            self._save_manifest(manifest)

            # 5. 保存处理后的文档到 processed/
            self._save_processed(result.documents)

            result.success = True
            self._report_progress(
                "done",
                f"采集完成: {result.total_new}新增, {result.total_updated}更新, {result.total_skipped}跳过",
                100,
            )

        except Exception as e:
            logger.error(f"[{self.source_name}] 采集失败: {e}")
            result.errors.append(str(e))
        finally:
            result.duration_seconds = time.time() - start_time
            await self._close_client()

        return result

    # ==================== HTTP 工具 ====================

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.request_timeout, connect=10.0),
                headers={"User-Agent": random.choice(self.USER_AGENTS)},
                follow_redirects=True,
            )
        return self._client

    async def _close_client(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """带指数退避重试的 HTTP 请求"""
        client = await self._get_client()
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # 限速
                if attempt > 0 or self.rate_limit > 0:
                    delay = self.rate_limit + random.uniform(0, 1.0)
                    if attempt > 0:
                        delay = min(30, (2 ** attempt) + random.uniform(0, 2))
                    await asyncio.sleep(delay)

                resp = await client.request(method, url, **kwargs)

                # 429 速率限制
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 10))
                    logger.warning(
                        f"[{self.source_name}] 429 限速，等待 {retry_after}s"
                    )
                    await asyncio.sleep(retry_after)
                    continue

                resp.raise_for_status()
                return resp

            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                last_error = e
                logger.warning(
                    f"[{self.source_name}] 请求失败 (第{attempt+1}次): {url} - {e}"
                )

        raise last_error or RuntimeError(f"请求失败: {url}")

    async def _download_file(self, url: str, save_path: Path) -> Path:
        """下载文件到指定路径"""
        resp = await self._request_with_retry("GET", url)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(resp.content)
        logger.info(f"[{self.source_name}] 已下载: {save_path.name} ({len(resp.content)} bytes)")
        return save_path

    # ==================== Manifest 管理 ====================

    def _load_manifest(self) -> CollectorManifest:
        if self._manifest:
            return self._manifest

        if self.manifest_path.exists():
            try:
                data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
                self._manifest = CollectorManifest(**data)
            except Exception as e:
                logger.warning(f"Manifest 加载失败，创建新的: {e}")
                self._manifest = CollectorManifest(source_name=self.source_name)
        else:
            self._manifest = CollectorManifest(source_name=self.source_name)

        return self._manifest

    def _save_manifest(self, manifest: CollectorManifest):
        self._manifest = manifest
        self.manifest_path.write_text(
            json.dumps(asdict(manifest), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _is_unchanged(self, doc_id: str, content_hash: str) -> bool:
        """检查文档是否未变更"""
        manifest = self._load_manifest()
        return manifest.document_hashes.get(doc_id) == content_hash

    # ==================== 工具方法 ====================

    @staticmethod
    def content_hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _save_processed(self, documents: List[ParsedDocument]):
        """保存解析后的文档为JSON文件"""
        if not documents:
            return
        output_path = self.processed_dir / f"{self.source_name}_{datetime.now().strftime('%Y%m%d')}.json"
        data = [doc.to_dict() for doc in documents]
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(f"[{self.source_name}] 已保存 {len(data)} 条文档到 {output_path}")

    def _report_progress(self, stage: str, message: str, progress: int):
        logger.info(f"[{self.source_name}] [{stage}] {message} ({progress}%)")
        if self._progress_callback:
            try:
                self._progress_callback(stage, message, progress)
            except Exception:
                pass

    # ==================== 法律文本处理工具 ====================

    @staticmethod
    def extract_cross_references(text: str) -> List[str]:
        """从法律文本中提取交叉引用"""
        import re

        patterns = [
            r"依据《([^》]+)》",
            r"根据《([^》]+)》",
            r"参照《([^》]+)》",
            r"依照《([^》]+)》",
            r"《([^》]+)》(?:第[一二三四五六七八九十百千\d]+条)?(?:的)?规定",
        ]

        refs = set()
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                ref = match.group(0)
                refs.add(ref)

        return list(refs)

    @staticmethod
    def normalize_law_name(name: str) -> str:
        """标准化法律名称（简称 → 全称）"""
        # 复用 legal_citation.py 中的映射
        LAW_NAME_MAP = {
            "民法典": "中华人民共和国民法典",
            "合同法": "中华人民共和国合同法",
            "劳动合同法": "中华人民共和国劳动合同法",
            "劳动法": "中华人民共和国劳动法",
            "公司法": "中华人民共和国公司法",
            "刑法": "中华人民共和国刑法",
            "民事诉讼法": "中华人民共和国民事诉讼法",
            "刑事诉讼法": "中华人民共和国刑事诉讼法",
            "行政诉讼法": "中华人民共和国行政诉讼法",
            "消费者权益保护法": "中华人民共和国消费者权益保护法",
            "数据安全法": "中华人民共和国数据安全法",
            "个人信息保护法": "中华人民共和国个人信息保护法",
            "网络安全法": "中华人民共和国网络安全法",
            "专利法": "中华人民共和国专利法",
            "商标法": "中华人民共和国商标法",
            "著作权法": "中华人民共和国著作权法",
            "保险法": "中华人民共和国保险法",
            "证券法": "中华人民共和国证券法",
        }
        return LAW_NAME_MAP.get(name, name)

    @staticmethod
    def map_law_category_to_knowledge_type(category: str) -> str:
        """将法规分类映射为 KnowledgeType value"""
        category_map = {
            "宪法": "law",
            "法律": "law",
            "行政法规": "regulation",
            "地方性法规": "regulation",
            "部门规章": "regulation",
            "司法解释": "interpretation",
            "合同模板": "template",
            "合同范本": "template",
        }
        for key, value in category_map.items():
            if key in category:
                return value
        return "law"
