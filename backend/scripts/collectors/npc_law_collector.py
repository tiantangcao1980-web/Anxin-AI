# -*- coding: utf-8 -*-
"""
国家法律法规数据库增量采集器

数据源: https://flk.npc.gov.cn/
内容: 宪法、法律、行政法规、地方性法规、部门规章等
接口: 非公开 REST API（由 law-datasets 项目发现并文档化）

该采集器作为 law_datasets_collector 的增量补充，
获取 law-datasets 最后更新（2023-09）之后新增或修改的法规。
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from loguru import logger

from .base_collector import BaseCollector, ParsedDocument


class NpcLawCollector(BaseCollector):
    """国家法律法规数据库增量采集器"""

    source_name = "npc-laws"
    knowledge_type = "law"
    rate_limit = 3.0  # 保守限速

    API_BASE = "https://flk.npc.gov.cn/api"

    # 法规类型及API参数
    LAW_TYPES = {
        "xf": ("宪法", "law"),
        "fl": ("法律", "law"),
        "xzfg": ("行政法规", "regulation"),
        "dfxfg": ("地方性法规", "regulation"),
        "bmgz": ("部门规章", "regulation"),
        "sfjs": ("司法解释", "interpretation"),
    }

    async def download(self) -> List[Path]:
        """通过 API 获取法规列表和全文"""
        manifest = self._load_manifest()
        # 确定增量起始时间（默认从2023-09-01开始，即law-datasets最后更新后）
        since = manifest.last_sync_at or "2023-09-01"

        all_laws = []

        for type_code, (type_name, _) in self.LAW_TYPES.items():
            self._report_progress(
                "download",
                f"正在获取{type_name}列表...",
                int(20 + list(self.LAW_TYPES.keys()).index(type_code) / len(self.LAW_TYPES) * 50),
            )

            try:
                laws = await self._fetch_law_type(type_code, type_name, since)
                all_laws.extend(laws)
            except Exception as e:
                logger.error(f"获取{type_name}失败: {e}")
                continue

        if all_laws:
            output_path = self.raw_dir / f"npc_laws_{datetime.now().strftime('%Y%m%d')}.json"
            output_path.write_text(
                json.dumps(all_laws, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(f"共获取 {len(all_laws)} 条法规")
            return [output_path]

        return []

    async def _fetch_law_type(
        self, type_code: str, type_name: str, since: str
    ) -> List[dict]:
        """获取某类法规的列表和详情"""
        laws = []
        page = 1
        page_size = 10

        while True:
            try:
                # 列表API
                params = {
                    "type": type_code,
                    "page": page,
                    "size": page_size,
                    "searchType": "title;vague",
                    "sortTr": "f_bbrq_s;desc",  # 按发布日期降序
                }

                resp = await self._request_with_retry(
                    "GET", f"{self.API_BASE}/", params=params
                )
                data = resp.json()

                result = data.get("result", {})
                items = result.get("data", [])

                if not items:
                    break

                for item in items:
                    # 检查发布日期是否在 since 之后
                    publish_date = item.get("publish", "") or item.get("f_bbrq_s", "")
                    if publish_date and publish_date < since:
                        # 因为按日期降序，后面的都更早，可以停止
                        return laws

                    # 获取详情
                    law_id = item.get("id", "")
                    if law_id:
                        detail = await self._fetch_law_detail(law_id)
                        if detail:
                            detail["type_code"] = type_code
                            detail["type_name"] = type_name
                            laws.append(detail)

                # 检查是否有更多页
                total_count = result.get("totalSizes", 0) or result.get("size", 0)
                if page * page_size >= total_count:
                    break

                page += 1

            except Exception as e:
                logger.warning(f"获取{type_name}第{page}页失败: {e}")
                break

        return laws

    async def _fetch_law_detail(self, law_id: str) -> Optional[dict]:
        """获取法规详情"""
        try:
            resp = await self._request_with_retry(
                "POST",
                f"{self.API_BASE}/detail",
                data={"id": law_id},
            )
            data = resp.json()
            result = data.get("result", {})

            title = result.get("title", "")
            body = result.get("body", "") or ""

            # body 可能包含HTML，需要清理
            if "<" in body:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(body, "html.parser")
                body = soup.get_text(separator="\n", strip=True)

            return {
                "id": law_id,
                "title": title,
                "body": body,
                "authority": result.get("office", ""),
                "publish": result.get("publish", ""),
                "valid_from": result.get("expiry", ""),
                "status": result.get("status", ""),
                "url": f"https://flk.npc.gov.cn/detail2.html?ZmY={law_id}",
            }

        except Exception as e:
            logger.warning(f"获取法规详情失败 [{law_id}]: {e}")
            return None

    async def parse(self, downloaded_files: List[Path]) -> List[ParsedDocument]:
        """解析下载的法规数据"""
        documents = []

        for file_path in downloaded_files:
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    continue

                for item in data:
                    doc = self._parse_law_item(item)
                    if doc:
                        documents.append(doc)
            except Exception as e:
                logger.warning(f"解析文件失败 {file_path}: {e}")

        logger.info(f"共解析出 {len(documents)} 条增量法规")
        return documents

    def _parse_law_item(self, item: dict) -> Optional[ParsedDocument]:
        """解析单条法规"""
        title = item.get("title", "").strip()
        body = item.get("body", "").strip()

        if not title or not body:
            return None

        law_id = item.get("id", self.content_hash(title)[:16])
        doc_id = f"npc_{law_id}"

        type_name = item.get("type_name", "法律")
        knowledge_type = self.map_law_category_to_knowledge_type(type_name)
        cross_refs = self.extract_cross_references(body)

        return ParsedDocument(
            doc_id=doc_id,
            title=title,
            content=body,
            source="国家法律法规数据库",
            source_url=item.get("url", f"https://flk.npc.gov.cn/detail2.html?ZmY={law_id}"),
            knowledge_type=knowledge_type,
            law_category=type_name,
            effective_date=item.get("valid_from", "") or item.get("publish", ""),
            issuing_authority=item.get("authority", ""),
            tags=[type_name],
            cross_references=cross_refs,
            extra_metadata={
                "publish_date": item.get("publish", ""),
                "status": item.get("status", ""),
                "type_code": item.get("type_code", ""),
            },
        )
