# -*- coding: utf-8 -*-
"""
国务院政策文件 + 人社部劳动法规 + 市监总局法规 采集器

数据源:
  - https://www.gov.cn/zhengce/ (国务院政策文件)
  - http://www.mohrss.gov.cn/xxgk2020/fdzdgknr/fgwj/ (人社部劳动法规)
  - https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/ (市监总局法规)

覆盖中小企业高频合规场景：用工合规、市场监管。
"""

import re
import json
from pathlib import Path
from typing import List, Optional

from bs4 import BeautifulSoup
from loguru import logger

from .base_collector import BaseCollector, ParsedDocument


class PolicyCollector(BaseCollector):
    """多源政策法规采集器"""

    source_name = "policy-documents"
    knowledge_type = "policy"
    rate_limit = 3.0

    # 多数据源配置
    SOURCES = [
        {
            "name": "国务院政策文件",
            "base_url": "https://www.gov.cn",
            "list_url": "https://www.gov.cn/zhengce/zhengceku/index.htm",
            "category": "policy",
            "authority": "国务院",
            "knowledge_type": "policy",
        },
        {
            "name": "人力资源社会保障部法规",
            "base_url": "http://www.mohrss.gov.cn",
            "list_url": "http://www.mohrss.gov.cn/xxgk2020/fdzdgknr/fgwj/",
            "category": "labor_regulation",
            "authority": "人力资源和社会保障部",
            "knowledge_type": "regulation",
            "tags_extra": ["劳动法", "用工合规", "社会保障"],
        },
        {
            "name": "国家市场监督管理总局法规",
            "base_url": "https://www.samr.gov.cn",
            "list_url": "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/",
            "category": "market_regulation",
            "authority": "国家市场监督管理总局",
            "knowledge_type": "regulation",
            "tags_extra": ["市场监管", "反不正当竞争"],
        },
    ]

    async def download(self) -> List[Path]:
        """从多个数据源爬取"""
        all_items = []

        for i, source in enumerate(self.SOURCES):
            self._report_progress(
                "download",
                f"正在爬取 {source['name']}...",
                int(10 + i / len(self.SOURCES) * 60),
            )

            try:
                items = await self._crawl_source(source)
                all_items.extend(items)
            except Exception as e:
                logger.error(f"爬取 {source['name']} 失败: {e}")
                continue

        if all_items:
            output_path = self.raw_dir / "policy_items_raw.json"
            output_path.write_text(
                json.dumps(all_items, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(f"共爬取 {len(all_items)} 条政策法规")
            return [output_path]

        return []

    async def _crawl_source(self, source: dict) -> List[dict]:
        """爬取单个数据源"""
        items = []
        page = 0
        max_pages = 20

        while page < max_pages:
            url = source["list_url"]
            if page > 0:
                # 不同网站分页方式不同
                if "gov.cn" in url:
                    url = url.replace("index.htm", f"index_{page}.htm")
                else:
                    url = f"{url}?page={page}"

            try:
                resp = await self._request_with_retry("GET", url)
                if resp.status_code == 404:
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                page_items = self._extract_items(soup, source)

                if not page_items:
                    break

                for item in page_items:
                    detail_url = item.get("url", "")
                    if detail_url and not detail_url.startswith("http"):
                        detail_url = f"{source['base_url']}{detail_url}"

                    if detail_url:
                        try:
                            detail = await self._crawl_detail(detail_url)
                            if detail:
                                detail.update({
                                    "source_name": source["name"],
                                    "category": source["category"],
                                    "authority": source["authority"],
                                    "knowledge_type": source["knowledge_type"],
                                    "tags_extra": source.get("tags_extra", []),
                                    "title": detail.get("title") or item.get("title", ""),
                                })
                                items.append(detail)
                        except Exception as e:
                            logger.debug(f"获取详情失败: {e}")

                page += 1

            except Exception as e:
                logger.warning(f"爬取 {source['name']} 第{page}页失败: {e}")
                break

        return items

    async def _crawl_detail(self, url: str) -> Optional[dict]:
        """爬取详情页"""
        resp = await self._request_with_retry("GET", url)
        soup = BeautifulSoup(resp.text, "html.parser")

        title = ""
        content = ""

        title_el = soup.find("h1") or soup.find("h2")
        if title_el:
            title = title_el.get_text(strip=True)

        content_el = (
            soup.find("div", class_=re.compile(r"content|article|pages_content", re.I))
            or soup.find("div", id=re.compile(r"UCAP-CONTENT|content|zoom", re.I))
            or soup.find("article")
        )
        if content_el:
            for tag in content_el.find_all(["script", "style"]):
                tag.decompose()
            content = content_el.get_text(separator="\n", strip=True)

        publish_date = ""
        date_match = re.search(r"(\d{4}[-年/]\d{1,2}[-月/]\d{1,2})", soup.get_text()[:500])
        if date_match:
            publish_date = date_match.group(1)

        if not title and not content:
            return None

        return {
            "title": title,
            "content": content,
            "url": url,
            "publish_date": publish_date,
        }

    def _extract_items(self, soup: BeautifulSoup, source: dict) -> List[dict]:
        """提取列表条目"""
        items = []
        for a in soup.find_all("a"):
            href = a.get("href", "")
            text = a.get_text(strip=True)

            if not text or len(text) < 4 or not href or href == "#":
                continue
            if "javascript" in href.lower():
                continue

            # 按源类型过滤
            if source["category"] == "policy":
                # 政策文件通常包含特定路径
                if "/zhengce/" not in href and "/content" not in href:
                    continue
            elif source["category"] in ("labor_regulation", "market_regulation"):
                if not any(ext in href for ext in [".shtml", ".html", ".htm"]):
                    continue

            items.append({"title": text, "url": href})

        return items[:50]  # 每页限制50条

    async def parse(self, downloaded_files: List[Path]) -> List[ParsedDocument]:
        """解析结果"""
        documents = []

        for file_path in downloaded_files:
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                for item in data:
                    doc = self._parse_item(item)
                    if doc:
                        documents.append(doc)
            except Exception as e:
                logger.warning(f"解析失败 {file_path}: {e}")

        return documents

    def _parse_item(self, item: dict) -> Optional[ParsedDocument]:
        """解析单条"""
        title = item.get("title", "").strip()
        content = item.get("content", "").strip()
        if not title:
            return None
        if not content:
            content = f"《{title}》\n\n（全文内容待补充）"

        doc_id = f"pol_{self.content_hash(title)[:16]}"
        kt = item.get("knowledge_type", "policy")
        tags = item.get("tags_extra", []) + [item.get("category", "")]

        return ParsedDocument(
            doc_id=doc_id,
            title=title,
            content=content,
            source=item.get("source_name", "政策法规"),
            source_url=item.get("url", ""),
            knowledge_type=kt,
            law_category=item.get("category", ""),
            effective_date=item.get("publish_date", ""),
            issuing_authority=item.get("authority", ""),
            tags=[t for t in tags if t],
            cross_references=self.extract_cross_references(content),
        )
