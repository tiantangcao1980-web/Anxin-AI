# -*- coding: utf-8 -*-
"""
GitHub law-datasets 采集器

数据源: https://github.com/twang2218/law-datasets
内容: 国家法律法规数据库爬取的 22,552 条法律法规全文
格式: JSON 数组，每条含标题/发布机关/日期/分类/全文(Markdown)

这是优先级最高的数据源，可直接下载ZIP包解析。
"""

import json
import zipfile
from pathlib import Path
from typing import List

from loguru import logger

from .base_collector import BaseCollector, ParsedDocument


class LawDatasetsCollector(BaseCollector):
    """GitHub 法律数据集采集器"""

    source_name = "law-datasets"
    knowledge_type = "law"

    REPO_ZIP_URL = "https://github.com/twang2218/law-datasets/archive/refs/heads/main.zip"
    # 备用镜像（如GitHub不可达）
    MIRROR_URLS = [
        "https://gh-proxy.com/https://github.com/twang2218/law-datasets/archive/refs/heads/main.zip",
        "https://ghproxy.net/https://github.com/twang2218/law-datasets/archive/refs/heads/main.zip",
    ]

    # LFS 文件的直接下载 URL（GitHub raw 会重定向到 LFS 存储）
    LAWS_JSON_ZIP_URL = "https://github.com/twang2218/law-datasets/raw/main/law-and-regulations/laws.json.zip"
    LAWS_JSON_ZIP_MIRRORS = [
        "https://gh-proxy.com/https://github.com/twang2218/law-datasets/raw/main/law-and-regulations/laws.json.zip",
    ]

    async def download(self) -> List[Path]:
        """下载 laws.json.zip（Git LFS 大文件）"""
        json_path = self.raw_dir / "laws.json"
        zip_path = self.raw_dir / "laws.json.zip"

        # 如果 laws.json 已存在且 manifest 有记录，跳过
        manifest = self._load_manifest()
        if json_path.exists() and json_path.stat().st_size > 1_000_000 and manifest.last_sync_hash:
            logger.info(f"laws.json 已存在 ({json_path.stat().st_size / 1024 / 1024:.0f}MB)，跳过下载")
            return [json_path]

        # 如果 ZIP 已存在且足够大，直接解压
        if zip_path.exists() and zip_path.stat().st_size > 1_000_000:
            logger.info("laws.json.zip 已存在，直接解压...")
        else:
            # 下载 laws.json.zip (通过 GitHub LFS raw URL)
            urls_to_try = [self.LAWS_JSON_ZIP_URL] + self.LAWS_JSON_ZIP_MIRRORS
            import subprocess
            downloaded = False
            for url in urls_to_try:
                try:
                    self._report_progress("download", f"正在下载 laws.json.zip ({url[:50]}...)", 15)
                    # 使用 curl 下载大文件（httpx 对大文件不太友好）
                    result = subprocess.run(
                        ["curl", "-L", "-o", str(zip_path), url],
                        capture_output=True, text=True, timeout=600,
                    )
                    if zip_path.exists() and zip_path.stat().st_size > 1_000_000:
                        downloaded = True
                        logger.info(f"下载完成: {zip_path.stat().st_size / 1024 / 1024:.1f} MB")
                        break
                    else:
                        logger.warning(f"下载文件过小: {zip_path.stat().st_size} bytes")
                except Exception as e:
                    logger.warning(f"从 {url[:50]}... 下载失败: {e}")
                    continue

            if not downloaded:
                raise RuntimeError("所有下载源均失败")

        # 解压
        import zipfile
        self._report_progress("download", "正在解压 laws.json.zip...", 30)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extract("laws.json", self.raw_dir)
        logger.info(f"解压完成: {json_path.stat().st_size / 1024 / 1024:.0f} MB")

        # 记录 hash
        manifest.last_sync_hash = self.content_hash(str(json_path.stat().st_size))
        self._save_manifest(manifest)

        return [json_path]

    async def parse(self, downloaded_files: List[Path]) -> List[ParsedDocument]:
        """解析 laws.json 文件"""
        documents = []

        for file_path in downloaded_files:
            if not file_path.suffix == ".json":
                continue

            self._report_progress("parse", f"正在解析 {file_path.name}...", 45)

            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))

                if isinstance(data, list):
                    logger.info(f"解析 {file_path.name}: {len(data)} 条记录")
                    for item in data:
                        doc = self._parse_law_item(item)
                        if doc:
                            documents.append(doc)
                elif isinstance(data, dict):
                    doc = self._parse_law_item(data)
                    if doc:
                        documents.append(doc)

            except Exception as e:
                logger.error(f"解析文件 {file_path} 失败: {e}")

        logger.info(f"共解析出 {len(documents)} 条法律文档")
        return documents

    def _parse_law_item(self, item: dict) -> ParsedDocument:
        """解析单条法律记录"""
        # law-datasets 实际 JSON 格式:
        # {
        #   "id": "...",
        #   "title": "中华人民共和国民法典",
        #   "content": "全文markdown内容",
        #   "type": "法律",  # 或 "行政法规" / "司法解释" 等
        #   "office": "全国人民代表大会",
        #   "publish": "2020-05-28 00:00:00",
        #   "expiry": "",  # 失效日期
        #   "status": "有效",
        #   "url": "https://flk.npc.gov.cn/detail2.html?...",
        #   "download_link_word": "...",
        #   "download_link_html": "...",
        #   "download_link_pdf": "...",
        # }
        title = item.get("title", "").strip()
        body = item.get("content", "") or item.get("body", "") or ""
        if not title or not body:
            return None

        # 构建稳定 doc_id
        item_id = item.get("id", "") or self.content_hash(title)[:16]
        doc_id = f"ld_{item_id}"

        # 确定知识类型 — 实际字段名是 "type" 而非 "level"
        level = item.get("type", "") or item.get("level", "") or item.get("category", "") or ""
        knowledge_type = self.map_law_category_to_knowledge_type(level)

        # 提取交叉引用
        cross_refs = self.extract_cross_references(body)

        return ParsedDocument(
            doc_id=doc_id,
            title=title,
            content=body,
            source="国家法律法规数据库(GitHub镜像)",
            source_url=item.get("url", "") or f"https://flk.npc.gov.cn/detail2.html?ZmY={item_id}",
            knowledge_type=knowledge_type,
            law_category=level,
            effective_date=item.get("publish", "") or item.get("valid_from", ""),
            issuing_authority=item.get("office", "") or item.get("authority", "") or item.get("department", ""),
            tags=self._generate_tags(title, level),
            cross_references=cross_refs,
            extra_metadata={
                "publish_date": item.get("publish", ""),
                "status": item.get("status", ""),
                "level": level,
            },
        )

    @staticmethod
    def _generate_tags(title: str, level: str) -> List[str]:
        """根据标题和类别生成标签"""
        tags = []
        if level:
            tags.append(level)

        # 按关键词匹配领域标签
        domain_keywords = {
            "劳动": "劳动法",
            "合同": "合同法",
            "公司": "公司法",
            "知识产权": "知识产权",
            "专利": "知识产权",
            "商标": "知识产权",
            "著作权": "知识产权",
            "税": "税法",
            "环境": "环境法",
            "安全生产": "安全生产",
            "消费者": "消费者保护",
            "数据": "数据安全",
            "网络": "网络安全",
            "个人信息": "个人信息保护",
            "民事": "民事法",
            "刑事": "刑事法",
            "行政": "行政法",
            "婚姻": "婚姻家庭",
            "继承": "继承法",
            "物权": "物权法",
            "保险": "保险法",
            "证券": "证券法",
            "银行": "银行法",
            "土地": "土地法",
            "建设": "建设法",
            "教育": "教育法",
            "医疗": "医疗卫生",
            "食品": "食品安全",
        }
        for keyword, tag in domain_keywords.items():
            if keyword in title:
                tags.append(tag)

        return tags
