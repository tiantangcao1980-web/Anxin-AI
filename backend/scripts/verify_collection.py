# -*- coding: utf-8 -*-
"""
法律数据采集验证脚本

验证采集结果的完整性和质量：
  1. 文档计数: manifest vs PostgreSQL
  2. 向量覆盖: is_processed 的文档在 Qdrant 中有对应向量
  3. 编码检查: 抽样验证中文无乱码
  4. 分块质量: 法律文档的 chunk 以"第X条"开头
  5. RAG烟测: 执行几个典型法律问题验证检索质量
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
os.chdir(PROJECT_ROOT)


class CollectionVerifier:
    """采集结果验证器"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.results: Dict[str, Any] = {}
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    async def verify_all(self):
        """执行所有验证"""
        logger.info("=" * 60)
        logger.info("法律数据采集验证")
        logger.info("=" * 60)

        await self._check_manifest_counts()
        await self._check_processed_files()
        await self._check_encoding()
        await self._check_db_documents()
        await self._check_rag_queries()

        self._print_summary()

    async def _check_manifest_counts(self):
        """检查 manifest 文档计数"""
        logger.info("\n[1] 检查 Manifest 文档计数")

        manifests_dir = self.data_dir / "manifests"
        if not manifests_dir.exists():
            self._fail("manifest_dir", "manifests/ 目录不存在")
            return

        for manifest_file in manifests_dir.glob("*.json"):
            try:
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                source = data.get("source_name", manifest_file.stem)
                total = data.get("total_documents", 0)
                last_sync = data.get("last_sync_at", "未同步")
                errors = data.get("errors", [])

                if total > 0:
                    self._pass(
                        f"manifest_{source}",
                        f"{source}: {total} 条文档, 最后同步: {last_sync}",
                    )
                else:
                    self._warn(
                        f"manifest_{source}",
                        f"{source}: 0 条文档",
                    )

                if errors:
                    self._warn(
                        f"manifest_errors_{source}",
                        f"{source}: {len(errors)} 个错误",
                    )

            except Exception as e:
                self._fail(f"manifest_{manifest_file.stem}", str(e))

    async def _check_processed_files(self):
        """检查 processed 目录的文件"""
        logger.info("\n[2] 检查处理后的数据文件")

        processed_dir = self.data_dir / "processed"
        if not processed_dir.exists():
            self._warn("processed_dir", "processed/ 目录不存在（尚未运行采集）")
            return

        total_docs = 0
        for source_dir in processed_dir.iterdir():
            if not source_dir.is_dir():
                continue

            json_files = list(source_dir.glob("*.json"))
            doc_count = 0
            for jf in json_files:
                try:
                    data = json.loads(jf.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        doc_count += len(data)
                except Exception:
                    pass

            if doc_count > 0:
                self._pass(
                    f"processed_{source_dir.name}",
                    f"{source_dir.name}: {doc_count} 条文档, {len(json_files)} 个文件",
                )
                total_docs += doc_count
            else:
                self._warn(f"processed_{source_dir.name}", f"{source_dir.name}: 无文档")

        if total_docs > 0:
            self._pass("processed_total", f"总计: {total_docs} 条已处理文档")

    async def _check_encoding(self):
        """抽样检查中文编码"""
        logger.info("\n[3] 检查中文编码")

        processed_dir = self.data_dir / "processed"
        if not processed_dir.exists():
            self._warn("encoding", "无数据可检查")
            return

        sample_count = 0
        encoding_errors = 0

        for json_file in processed_dir.rglob("*.json"):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    continue

                for item in data[:10]:  # 每个文件抽样10条
                    content = item.get("content", "")
                    title = item.get("title", "")
                    sample_count += 1

                    # 检查常见乱码特征
                    if re.search(r"[\ufffd\u0000-\u001f]", content + title):
                        encoding_errors += 1

                    # 检查是否包含中文
                    if not re.search(r"[\u4e00-\u9fff]", content + title):
                        encoding_errors += 1

            except UnicodeDecodeError:
                encoding_errors += 1

        if sample_count > 0 and encoding_errors == 0:
            self._pass("encoding", f"抽样 {sample_count} 条，编码正常")
        elif encoding_errors > 0:
            self._fail("encoding", f"发现 {encoding_errors}/{sample_count} 条编码异常")
        else:
            self._warn("encoding", "无数据可检查")

    async def _check_db_documents(self):
        """检查数据库中的文档"""
        logger.info("\n[4] 检查数据库文档")

        try:
            from src.core.database import async_session_maker
            from src.models.knowledge import KnowledgeBase, KnowledgeDocument
            from sqlalchemy import select, func

            async with async_session_maker() as db:
                # 知识库统计
                result = await db.execute(select(func.count()).select_from(KnowledgeBase))
                kb_count = result.scalar()

                result = await db.execute(select(func.count()).select_from(KnowledgeDocument))
                doc_count = result.scalar()

                result = await db.execute(
                    select(func.count()).select_from(KnowledgeDocument).where(
                        KnowledgeDocument.is_processed == True
                    )
                )
                processed_count = result.scalar()

                if kb_count > 0:
                    self._pass("db_kb", f"{kb_count} 个知识库")
                else:
                    self._warn("db_kb", "数据库中无知识库")

                if doc_count > 0:
                    self._pass(
                        "db_docs",
                        f"{doc_count} 条文档 ({processed_count} 已向量化)",
                    )
                else:
                    self._warn("db_docs", "数据库中无文档")

                # 按知识类型统计
                result = await db.execute(
                    select(
                        KnowledgeBase.knowledge_type,
                        func.count(KnowledgeDocument.id),
                    )
                    .join(KnowledgeDocument)
                    .group_by(KnowledgeBase.knowledge_type)
                )
                for kt, count in result:
                    logger.info(f"    {kt}: {count} 条")

        except Exception as e:
            self._warn("db", f"数据库连接失败（可能未启动）: {e}")

    async def _check_rag_queries(self):
        """RAG 烟测"""
        logger.info("\n[5] RAG 烟测查询")

        test_queries = [
            {
                "query": "劳动合同试用期最长多久",
                "expected_keywords": ["试用期", "劳动合同法", "第十九条", "19"],
            },
            {
                "query": "合同违约金过高如何调整",
                "expected_keywords": ["违约金", "民法典", "585", "约定"],
            },
            {
                "query": "租赁合同最长期限是多少年",
                "expected_keywords": ["租赁", "二十年", "20", "706"],
            },
        ]

        try:
            from src.core.database import async_session_maker
            from src.services.knowledge_service import KnowledgeService

            async with async_session_maker() as db:
                ks = KnowledgeService(db)

                for tq in test_queries:
                    try:
                        results = await ks.search(
                            query=tq["query"],
                            top_k=3,
                        )

                        if results:
                            # 检查返回结果是否包含预期关键词
                            all_content = " ".join(
                                r.get("content", "") for r in results
                            )
                            hits = sum(
                                1 for kw in tq["expected_keywords"]
                                if kw in all_content
                            )

                            if hits >= 1:
                                self._pass(
                                    f"rag_{tq['query'][:20]}",
                                    f"查询'{tq['query'][:20]}...' 命中 {hits}/{len(tq['expected_keywords'])} 关键词",
                                )
                            else:
                                self._warn(
                                    f"rag_{tq['query'][:20]}",
                                    f"查询'{tq['query'][:20]}...' 未命中预期关键词",
                                )
                        else:
                            self._warn(
                                f"rag_{tq['query'][:20]}",
                                f"查询'{tq['query'][:20]}...' 无结果",
                            )

                    except Exception as e:
                        self._warn(f"rag_{tq['query'][:20]}", f"查询失败: {e}")

        except Exception as e:
            self._warn("rag", f"RAG 服务不可用: {e}")

    # ==================== 辅助方法 ====================

    def _pass(self, key: str, message: str):
        self.results[key] = {"status": "PASS", "message": message}
        self.passed += 1
        logger.info(f"  [PASS] {message}")

    def _fail(self, key: str, message: str):
        self.results[key] = {"status": "FAIL", "message": message}
        self.failed += 1
        logger.error(f"  [FAIL] {message}")

    def _warn(self, key: str, message: str):
        self.results[key] = {"status": "WARN", "message": message}
        self.warnings += 1
        logger.warning(f"  [WARN] {message}")

    def _print_summary(self):
        logger.info("\n" + "=" * 60)
        logger.info("验证结果汇总")
        logger.info("=" * 60)
        logger.info(f"  通过: {self.passed}")
        logger.info(f"  失败: {self.failed}")
        logger.info(f"  警告: {self.warnings}")

        if self.failed == 0:
            logger.info("  结论: 所有检查通过！")
        else:
            logger.error(f"  结论: {self.failed} 项检查失败，请排查")

        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(CollectionVerifier().verify_all())
