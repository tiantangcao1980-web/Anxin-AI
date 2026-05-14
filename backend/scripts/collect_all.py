# -*- coding: utf-8 -*-
"""
法律数据采集主控脚本

统一编排所有数据源的采集、导入、图谱构建流程。

使用方式:
    # 采集所有 T1 数据源（优先级最高）
    python scripts/collect_all.py --tier 1

    # 采集指定数据源
    python scripts/collect_all.py --sources law-datasets,contract-templates

    # 强制重新下载
    python scripts/collect_all.py --tier 1 --force

    # 仅下载不导入
    python scripts/collect_all.py --tier 1 --skip-import

    # 仅导入（从已下载的 processed/ 目录）
    python scripts/collect_all.py --import-only

    # 干跑（查看计划）
    python scripts/collect_all.py --tier 1 --dry-run

    # 构建知识图谱
    python scripts/collect_all.py --graph-only
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

# 设置项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
os.chdir(PROJECT_ROOT)

# 导入采集器
from scripts.collectors.law_datasets_collector import LawDatasetsCollector
from scripts.collectors.contract_template_collector import ContractTemplateCollector
from scripts.collectors.admin_regulation_collector import AdminRegulationCollector
from scripts.collectors.npc_law_collector import NpcLawCollector
from scripts.collectors.spp_collector import SppCollector
from scripts.collectors.policy_collector import PolicyCollector
from scripts.collectors.open_dataset_collector import OpenDatasetCollector
from scripts.collectors.base_collector import CollectorResult


# ==================== 采集器注册表 ====================

# 按层级（Tier）组织，层级内按优先级排序
COLLECTOR_REGISTRY = {
    1: [
        {
            "name": "law-datasets",
            "class": LawDatasetsCollector,
            "kb_name": "法律法规库",
            "description": "GitHub法律数据集（22,552条法律法规全文）",
        },
        {
            "name": "contract-templates",
            "class": ContractTemplateCollector,
            "kb_name": "合同示范文本库",
            "description": "国家市场监管总局合同示范文本",
        },
        {
            "name": "admin-regulations",
            "class": AdminRegulationCollector,
            "kb_name": "行政法规库",
            "description": "司法部现行有效行政法规（611部）",
        },
    ],
    2: [
        {
            "name": "npc-laws",
            "class": NpcLawCollector,
            "kb_name": "法律法规库",  # 与law-datasets共享同一知识库
            "description": "国家法律法规数据库增量更新",
        },
        {
            "name": "spp-interpretations",
            "class": SppCollector,
            "kb_name": "司法解释库",
            "description": "最高检司法解释和规范性文件",
        },
    ],
    3: [
        {
            "name": "policy-documents",
            "class": PolicyCollector,
            "kb_name": "政策法规库",
            "description": "国务院政策+人社部劳动法规+市监总局法规",
        },
    ],
    4: [
        {
            "name": "open-datasets",
            "class": OpenDatasetCollector,
            "kb_name": "法律知识库",
            "description": "开源法律数据集（DISC-LawLLM、CAIL等）",
        },
    ],
}


def get_collector_info(name: str) -> Optional[dict]:
    """按名称查找采集器信息"""
    for tier, collectors in COLLECTOR_REGISTRY.items():
        for c in collectors:
            if c["name"] == name:
                return {**c, "tier": tier}
    return None


# ==================== 主流程 ====================


async def run_collection(
    tier: Optional[int] = None,
    sources: Optional[List[str]] = None,
    force: bool = False,
    skip_import: bool = False,
    skip_graph: bool = False,
    import_only: bool = False,
    graph_only: bool = False,
    dry_run: bool = False,
    data_dir: str = "data",
):
    """执行采集主流程"""
    start_time = time.time()

    # 确定要运行的采集器
    targets = _resolve_targets(tier, sources)

    if not targets and not graph_only:
        logger.error("未找到匹配的采集器。使用 --tier N 或 --sources name1,name2")
        return

    # 干跑模式
    if dry_run:
        _print_dry_run(targets)
        return

    # 仅构建图谱
    if graph_only:
        logger.info("=" * 60)
        logger.info("仅构建知识图谱")
        logger.info("=" * 60)
        from scripts.build_law_graph import LawGraphBuilder
        builder = LawGraphBuilder()
        stats = await builder.build_from_processed_files(data_dir)
        logger.info(f"图谱构建完成: {json.dumps(stats, ensure_ascii=False)}")
        return

    results: Dict[str, CollectorResult] = {}

    # 仅导入模式
    if import_only:
        logger.info("=" * 60)
        logger.info("仅导入模式：从 processed/ 目录导入")
        logger.info("=" * 60)
        await _import_from_processed(targets, data_dir)
        return

    # 正常流程：采集 → 导入 → 图谱
    for target in targets:
        name = target["name"]
        tier_num = target["tier"]
        logger.info("=" * 60)
        logger.info(f"[T{tier_num}] {name}: {target['description']}")
        logger.info("=" * 60)

        try:
            # 1. 采集
            collector_cls = target["class"]
            collector = collector_cls(data_dir=data_dir)
            result = await collector.collect(force=force)
            results[name] = result

            if not result.success:
                logger.error(f"[{name}] 采集失败: {result.errors}")
                continue

            logger.info(
                f"[{name}] 采集完成: "
                f"{result.total_parsed}解析, "
                f"{result.total_new}新增, "
                f"{result.total_updated}更新, "
                f"{result.total_skipped}跳过 "
                f"({result.duration_seconds:.1f}s)"
            )

            # 2. 导入
            if not skip_import and result.documents:
                logger.info(f"[{name}] 开始导入 {len(result.documents)} 条文档...")
                try:
                    from scripts.import_pipeline import ImportPipeline

                    pipeline = ImportPipeline()
                    import_result = await pipeline.import_documents(
                        documents=[doc.to_dict() for doc in result.documents],
                        kb_name=target["kb_name"],
                        knowledge_type=collector.knowledge_type,
                        description=target["description"],
                    )

                    if import_result.get("success"):
                        logger.info(
                            f"[{name}] 导入完成: "
                            f"{import_result['imported']}新增, "
                            f"{import_result['updated']}更新, "
                            f"{import_result['skipped']}跳过"
                        )
                    else:
                        logger.error(f"[{name}] 导入失败: {import_result.get('error')}")

                except Exception as e:
                    logger.error(f"[{name}] 导入异常: {e}")

        except Exception as e:
            logger.error(f"[{name}] 执行异常: {e}")
            import traceback
            traceback.print_exc()

    # 3. 构建知识图谱
    if not skip_graph:
        logger.info("=" * 60)
        logger.info("构建知识图谱...")
        logger.info("=" * 60)
        try:
            from scripts.build_law_graph import LawGraphBuilder
            builder = LawGraphBuilder()
            graph_stats = await builder.build_from_processed_files(data_dir)
            logger.info(f"图谱构建完成: {json.dumps(graph_stats, ensure_ascii=False)}")
        except Exception as e:
            logger.warning(f"图谱构建失败（可稍后单独运行）: {e}")

    # 4. 汇总报告
    elapsed = time.time() - start_time
    _print_summary(results, elapsed)


async def _import_from_processed(targets: List[dict], data_dir: str):
    """从 processed/ 目录导入已有数据"""
    processed_dir = Path(data_dir) / "processed"

    for target in targets:
        source_dir = processed_dir / target["name"]
        if not source_dir.exists():
            logger.warning(f"[{target['name']}] 无 processed 数据，跳过")
            continue

        json_files = list(source_dir.glob("*.json"))
        if not json_files:
            continue

        # 合并所有JSON文件
        all_docs = []
        for jf in json_files:
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    all_docs.extend(data)
            except Exception as e:
                logger.warning(f"读取 {jf} 失败: {e}")

        if not all_docs:
            continue

        logger.info(f"[{target['name']}] 导入 {len(all_docs)} 条文档到 {target['kb_name']}...")
        try:
            from scripts.import_pipeline import ImportPipeline
            pipeline = ImportPipeline()
            result = await pipeline.import_documents(
                documents=all_docs,
                kb_name=target["kb_name"],
                knowledge_type=target["class"].knowledge_type if hasattr(target["class"], "knowledge_type") else "law",
                description=target["description"],
            )
            logger.info(f"[{target['name']}] 导入结果: {json.dumps({k: v for k, v in result.items() if k != 'error_details'}, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f"[{target['name']}] 导入失败: {e}")


def _resolve_targets(
    tier: Optional[int], sources: Optional[List[str]]
) -> List[dict]:
    """解析目标采集器列表"""
    targets = []

    if sources:
        for name in sources:
            info = get_collector_info(name.strip())
            if info:
                targets.append(info)
            else:
                logger.warning(f"未知数据源: {name}")

    elif tier is not None:
        for t in range(1, tier + 1):
            for c in COLLECTOR_REGISTRY.get(t, []):
                targets.append({**c, "tier": t})

    else:
        # 默认：所有层级
        for t, collectors in sorted(COLLECTOR_REGISTRY.items()):
            for c in collectors:
                targets.append({**c, "tier": t})

    return targets


def _print_dry_run(targets: List[dict]):
    """打印干跑计划"""
    print("\n" + "=" * 60)
    print("采集计划（干跑模式，不实际执行）")
    print("=" * 60)

    for target in targets:
        print(f"\n  [T{target['tier']}] {target['name']}")
        print(f"    描述: {target['description']}")
        print(f"    目标知识库: {target['kb_name']}")
        print(f"    采集器类: {target['class'].__name__}")

    print(f"\n  共 {len(targets)} 个数据源待采集")
    print("=" * 60)


def _print_summary(results: Dict[str, CollectorResult], elapsed: float):
    """打印汇总报告"""
    print("\n" + "=" * 60)
    print("采集汇总报告")
    print("=" * 60)

    total_parsed = 0
    total_new = 0
    total_updated = 0
    total_errors = 0

    for name, result in results.items():
        status = "成功" if result.success else "失败"
        print(
            f"  [{status}] {name}: "
            f"{result.total_parsed}解析, "
            f"{result.total_new}新增, "
            f"{result.total_updated}更新, "
            f"{result.total_skipped}跳过, "
            f"{len(result.errors)}错误 "
            f"({result.duration_seconds:.1f}s)"
        )
        total_parsed += result.total_parsed
        total_new += result.total_new
        total_updated += result.total_updated
        total_errors += len(result.errors)

    print(f"\n  总计: {total_parsed}解析, {total_new}新增, {total_updated}更新, {total_errors}错误")
    print(f"  总耗时: {elapsed:.1f}s ({elapsed/60:.1f}min)")
    print("=" * 60)


# ==================== CLI 入口 ====================


def main():
    parser = argparse.ArgumentParser(
        description="安心智能助手 — 法律数据采集主控脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/collect_all.py --tier 1              # 采集T1数据源
  python scripts/collect_all.py --sources law-datasets # 采集指定源
  python scripts/collect_all.py --tier 1 --force       # 强制重新下载
  python scripts/collect_all.py --tier 1 --skip-import # 仅下载不导入
  python scripts/collect_all.py --import-only          # 仅导入已下载数据
  python scripts/collect_all.py --graph-only           # 仅构建知识图谱
  python scripts/collect_all.py --dry-run              # 查看计划
  python scripts/collect_all.py --list                 # 列出所有数据源

可用数据源:
  T1: law-datasets, contract-templates, admin-regulations
  T2: npc-laws, spp-interpretations
  T3: policy-documents
  T4: open-datasets
        """,
    )
    parser.add_argument("--tier", type=int, help="采集层级 (1-4)")
    parser.add_argument("--sources", type=str, help="指定数据源 (逗号分隔)")
    parser.add_argument("--force", action="store_true", help="强制重新下载")
    parser.add_argument("--skip-import", action="store_true", help="仅下载不导入")
    parser.add_argument("--skip-graph", action="store_true", help="跳过图谱构建")
    parser.add_argument("--import-only", action="store_true", help="仅从processed/导入")
    parser.add_argument("--graph-only", action="store_true", help="仅构建图谱")
    parser.add_argument("--dry-run", action="store_true", help="干跑模式")
    parser.add_argument("--data-dir", default="data", help="数据目录 (默认: data)")
    parser.add_argument("--list", action="store_true", help="列出所有数据源")

    args = parser.parse_args()

    if args.list:
        _print_dry_run(_resolve_targets(None, None))
        return

    sources = args.sources.split(",") if args.sources else None

    asyncio.run(
        run_collection(
            tier=args.tier,
            sources=sources,
            force=args.force,
            skip_import=args.skip_import,
            skip_graph=args.skip_graph,
            import_only=args.import_only,
            graph_only=args.graph_only,
            dry_run=args.dry_run,
            data_dir=args.data_dir,
        )
    )


if __name__ == "__main__":
    main()
