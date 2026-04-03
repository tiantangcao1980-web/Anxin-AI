# -*- coding: utf-8 -*-
"""
法律知识图谱构建器

从已导入的法律文档中提取交叉引用关系，构建 Neo4j 知识图谱。

节点类型:
  - Law: 法律/法规实体
  - Provision: 具体条款 (第X条)
  - Authority: 发布机关

关系类型:
  - REFERENCES: 法律A引用法律B
  - CONTAINS: 法律 → 条款
  - ISSUED_BY: 法律 → 发布机关
  - SUPERSEDES: 新法替代旧法
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


# ==================== 引用提取 ====================

# 引用模式
REFERENCE_PATTERNS = [
    # 《法律名称》第XXX条
    re.compile(r"《([^》]+)》第([一二三四五六七八九十百千\d]+)条"),
    # 依据/根据/参照《法律名称》
    re.compile(r"(?:依据|根据|参照|依照|按照)《([^》]+)》"),
    # 《法律名称》的规定
    re.compile(r"《([^》]+)》(?:的)?(?:有关|相关)?规定"),
]

# 已知的法律替代关系 (新法 → 旧法)
SUPERSEDES_MAP = {
    "中华人民共和国民法典": ["中华人民共和国合同法", "中华人民共和国物权法", "中华人民共和国担保法",
                        "中华人民共和国婚姻法", "中华人民共和国继承法", "中华人民共和国侵权责任法",
                        "中华人民共和国民法通则", "中华人民共和国民法总则", "中华人民共和国收养法"],
}


def extract_references_from_text(text: str) -> List[Dict[str, str]]:
    """从文本中提取法律引用"""
    refs = []
    seen = set()

    for pattern in REFERENCE_PATTERNS:
        for match in pattern.finditer(text):
            law_name = match.group(1)
            article = match.group(2) if match.lastindex >= 2 else None

            key = f"{law_name}_{article or ''}"
            if key in seen:
                continue
            seen.add(key)

            refs.append({
                "law_name": law_name,
                "article": f"第{article}条" if article else None,
                "raw": match.group(0),
            })

    return refs


# ==================== 图谱构建 ====================


class LawGraphBuilder:
    """法律知识图谱构建器"""

    def __init__(self):
        self._graph_service = None
        self._stats = {
            "laws_created": 0,
            "provisions_created": 0,
            "authorities_created": 0,
            "references_created": 0,
            "contains_created": 0,
            "issued_by_created": 0,
            "supersedes_created": 0,
            "errors": 0,
        }

    async def _get_graph_service(self):
        if self._graph_service is None:
            try:
                from src.services.graph_service import GraphService
                self._graph_service = GraphService()
                logger.info("Neo4j GraphService 初始化成功")
            except Exception as e:
                logger.error(f"Neo4j 不可用: {e}")
                return None
        return self._graph_service

    async def build_from_processed_files(self, data_dir: str = "data"):
        """从 processed/ 目录的JSON文件构建图谱"""
        processed_dir = Path(data_dir) / "processed"
        if not processed_dir.exists():
            logger.error(f"目录不存在: {processed_dir}")
            return self._stats

        gs = await self._get_graph_service()
        if not gs:
            logger.warning("Neo4j 不可用，跳过图谱构建")
            return self._stats

        # 收集所有文档
        all_docs = []
        for json_file in processed_dir.rglob("*.json"):
            try:
                docs = json.loads(json_file.read_text(encoding="utf-8"))
                if isinstance(docs, list):
                    all_docs.extend(docs)
            except Exception as e:
                logger.warning(f"读取文件失败 {json_file}: {e}")

        logger.info(f"共加载 {len(all_docs)} 条文档用于图谱构建")

        # 第一遍：创建法律节点和发布机关节点
        law_nodes: Dict[str, Dict] = {}
        authority_nodes: Set[str] = set()

        for doc in all_docs:
            title = doc.get("title", "")
            authority = doc.get("issuing_authority", "")
            effective_date = doc.get("effective_date", "")
            law_name = self._extract_law_name(title)

            if law_name and law_name not in law_nodes:
                law_nodes[law_name] = {
                    "name": law_name,
                    "effective_date": effective_date,
                    "issuing_authority": authority,
                    "knowledge_type": doc.get("knowledge_type", "law"),
                }

            if authority:
                authority_nodes.add(authority)

        # 创建节点
        for law_name, props in law_nodes.items():
            try:
                await gs.query_graph(
                    "MERGE (l:Law {name: $name}) "
                    "SET l.effective_date = $effective_date, "
                    "l.issuing_authority = $issuing_authority, "
                    "l.knowledge_type = $knowledge_type",
                    props,
                )
                self._stats["laws_created"] += 1
            except Exception as e:
                self._stats["errors"] += 1
                logger.debug(f"创建法律节点失败 [{law_name}]: {e}")

        for auth in authority_nodes:
            try:
                await gs.query_graph(
                    "MERGE (a:Authority {name: $name})",
                    {"name": auth},
                )
                self._stats["authorities_created"] += 1
            except Exception as e:
                self._stats["errors"] += 1

        # 第二遍：创建 ISSUED_BY 关系
        for law_name, props in law_nodes.items():
            auth = props.get("issuing_authority")
            if auth:
                try:
                    await gs.query_graph(
                        "MATCH (l:Law {name: $law_name}), (a:Authority {name: $auth}) "
                        "MERGE (l)-[:ISSUED_BY]->(a)",
                        {"law_name": law_name, "auth": auth},
                    )
                    self._stats["issued_by_created"] += 1
                except Exception:
                    pass

        # 第三遍：提取交叉引用，创建 REFERENCES 关系
        for doc in all_docs:
            content = doc.get("content", "")
            source_title = doc.get("title", "")
            source_law = self._extract_law_name(source_title)

            if not source_law:
                continue

            refs = extract_references_from_text(content)
            for ref in refs:
                target_law = ref["law_name"]
                if target_law == source_law:
                    continue  # 跳过自引用

                try:
                    await gs.query_graph(
                        "MERGE (s:Law {name: $source}) "
                        "MERGE (t:Law {name: $target}) "
                        "MERGE (s)-[:REFERENCES]->(t)",
                        {"source": source_law, "target": target_law},
                    )
                    self._stats["references_created"] += 1
                except Exception:
                    self._stats["errors"] += 1

        # 第四遍：创建 SUPERSEDES 关系
        for new_law, old_laws in SUPERSEDES_MAP.items():
            for old_law in old_laws:
                try:
                    await gs.query_graph(
                        "MERGE (n:Law {name: $new_law}) "
                        "MERGE (o:Law {name: $old_law}) "
                        "MERGE (n)-[:SUPERSEDES]->(o)",
                        {"new_law": new_law, "old_law": old_law},
                    )
                    self._stats["supersedes_created"] += 1
                except Exception:
                    pass

        logger.info(
            f"图谱构建完成: "
            f"{self._stats['laws_created']}法律, "
            f"{self._stats['authorities_created']}机关, "
            f"{self._stats['references_created']}引用关系, "
            f"{self._stats['supersedes_created']}替代关系, "
            f"{self._stats['errors']}错误"
        )
        return self._stats

    @staticmethod
    def _extract_law_name(title: str) -> str:
        """从标题中提取法律名称"""
        if not title:
            return ""
        # 去除常见前缀后缀
        name = title.strip()
        for suffix in ["（修正）", "（修订）", "(修正)", "(修订)", "（全文）", "（节选）"]:
            name = name.replace(suffix, "")
        return name.strip()


# ==================== CLI 入口 ====================


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="构建法律知识图谱")
    parser.add_argument("--data-dir", default="data", help="数据目录")

    args = parser.parse_args()
    os.chdir(Path(__file__).resolve().parent.parent)

    builder = LawGraphBuilder()
    stats = asyncio.run(builder.build_from_processed_files(args.data_dir))
    print(json.dumps(stats, ensure_ascii=False, indent=2))
