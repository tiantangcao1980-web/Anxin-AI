# -*- coding: utf-8 -*-
"""
开源法律数据集采集器

数据源:
  - DISC-LawLLM: https://github.com/FudanDISC/DISC-LawLLM
  - LaWGPT: https://github.com/pengxiao-song/LaWGPT
  - CAIL: https://github.com/china-ai-law-challenge/CAIL

主要用于补充法律问答数据、案例分析数据，提升 RAG 的问答质量。
"""

import json
import zipfile
import io
from pathlib import Path
from typing import List, Optional

from loguru import logger

from .base_collector import BaseCollector, ParsedDocument


class OpenDatasetCollector(BaseCollector):
    """开源法律数据集采集器"""

    source_name = "open-datasets"
    knowledge_type = "article"
    rate_limit = 1.0

    # 数据集下载配置
    DATASETS = [
        {
            "name": "DISC-LawLLM-法律问答",
            "url": "https://github.com/FudanDISC/DISC-LawLLM/archive/refs/heads/main.zip",
            "mirror": "https://gh-proxy.com/https://github.com/FudanDISC/DISC-LawLLM/archive/refs/heads/main.zip",
            "data_files": ["*.json", "*.jsonl"],
            "knowledge_type": "article",
            "parser": "_parse_disc_lawllm",
        },
        {
            "name": "CAIL-案例数据",
            "url": "https://github.com/china-ai-law-challenge/CAIL2018/archive/refs/heads/master.zip",
            "mirror": "https://gh-proxy.com/https://github.com/china-ai-law-challenge/CAIL2018/archive/refs/heads/master.zip",
            "data_files": ["*.json"],
            "knowledge_type": "case",
            "parser": "_parse_cail",
        },
    ]

    async def download(self) -> List[Path]:
        """下载开源数据集"""
        downloaded = []

        for i, dataset in enumerate(self.DATASETS):
            self._report_progress(
                "download",
                f"正在下载 {dataset['name']}...",
                int(10 + i / len(self.DATASETS) * 60),
            )

            zip_path = self.raw_dir / f"{dataset['name'].replace('/', '_')}.zip"

            # 尝试主URL和镜像URL
            for url in [dataset["url"], dataset.get("mirror", "")]:
                if not url:
                    continue
                try:
                    resp = await self._request_with_retry("GET", url)
                    zip_path.write_bytes(resp.content)
                    downloaded.append(zip_path)
                    logger.info(f"下载成功: {dataset['name']} ({len(resp.content)/1024/1024:.1f}MB)")
                    break
                except Exception as e:
                    logger.warning(f"下载失败 {url}: {e}")
                    continue

        return downloaded

    async def parse(self, downloaded_files: List[Path]) -> List[ParsedDocument]:
        """解析下载的数据集"""
        documents = []

        for zip_path in downloaded_files:
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    # 查找JSON数据文件
                    json_files = [
                        f for f in zf.namelist()
                        if f.endswith(".json") or f.endswith(".jsonl")
                    ]

                    for json_file in json_files:
                        # 跳过非数据文件
                        if any(skip in json_file.lower() for skip in [
                            "package.json", "readme", "config", ".github",
                            "node_modules", "test", "example"
                        ]):
                            continue

                        try:
                            raw = zf.read(json_file).decode("utf-8")
                            docs = self._parse_json_data(raw, json_file)
                            documents.extend(docs)
                        except Exception as e:
                            logger.debug(f"解析 {json_file} 失败: {e}")

            except Exception as e:
                logger.warning(f"处理ZIP失败 {zip_path}: {e}")

        # 限制总量（开源数据集可能非常大）
        max_docs = 5000
        if len(documents) > max_docs:
            logger.info(f"数据集文档量 ({len(documents)}) 超过上限 {max_docs}，截取前 {max_docs} 条")
            documents = documents[:max_docs]

        logger.info(f"共解析出 {len(documents)} 条数据集文档")
        return documents

    def _parse_json_data(self, raw: str, filename: str) -> List[ParsedDocument]:
        """解析JSON/JSONL数据"""
        documents = []

        # JSONL 格式
        if filename.endswith(".jsonl"):
            for line_num, line in enumerate(raw.strip().split("\n")):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    doc = self._item_to_document(item, filename, line_num)
                    if doc:
                        documents.append(doc)
                except json.JSONDecodeError:
                    continue
        else:
            # JSON 格式
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    for i, item in enumerate(data):
                        doc = self._item_to_document(item, filename, i)
                        if doc:
                            documents.append(doc)
                elif isinstance(data, dict):
                    # 可能是嵌套结构 {"data": [...]}
                    for key in ["data", "train", "test", "dev", "items"]:
                        if key in data and isinstance(data[key], list):
                            for i, item in enumerate(data[key]):
                                doc = self._item_to_document(item, filename, i)
                                if doc:
                                    documents.append(doc)
                            break
            except json.JSONDecodeError:
                pass

        return documents

    def _item_to_document(
        self, item: dict, filename: str, index: int
    ) -> Optional[ParsedDocument]:
        """将数据集条目转为 ParsedDocument"""
        if not isinstance(item, dict):
            return None

        # 尝试多种字段名
        title = (
            item.get("title", "")
            or item.get("question", "")
            or item.get("instruction", "")
            or item.get("fact", "")[:100] if item.get("fact") else ""
        )

        content = (
            item.get("content", "")
            or item.get("answer", "")
            or item.get("output", "")
            or item.get("fact", "")
        )

        # 对于问答数据，合并问题和回答
        question = item.get("question", "") or item.get("instruction", "")
        answer = item.get("answer", "") or item.get("output", "")
        if question and answer and not content:
            content = f"问题：{question}\n\n回答：{answer}"
            title = title or question[:100]

        if not content or len(content) < 20:
            return None

        if not title:
            title = content[:80] + "..."

        doc_id = f"od_{self.content_hash(f'{filename}_{index}')[:16]}"

        # 判断知识类型
        kt = "article"
        if any(key in item for key in ["fact", "accusation", "relevant_articles"]):
            kt = "case"
        elif "法" in title or "条例" in title:
            kt = "law"

        tags = ["开源数据集"]
        # CAIL 数据特有字段
        if "accusation" in item:
            tags.append("刑事案例")
            tags.append(str(item.get("accusation", "")))
        if "relevant_articles" in item:
            tags.append("案例分析")

        return ParsedDocument(
            doc_id=doc_id,
            title=title[:500],
            content=content,
            source=f"开源数据集({filename.split('/')[0]})",
            source_url="",
            knowledge_type=kt,
            tags=tags,
            extra_metadata={
                "dataset_file": filename,
                "original_index": index,
            },
        )
