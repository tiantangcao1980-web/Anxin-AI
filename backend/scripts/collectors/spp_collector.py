# -*- coding: utf-8 -*-
"""
最高人民检察院法律法规库采集器

数据源: https://www.spp.gov.cn/spp/flfgk/index.shtml
内容: 宪法、法律、司法解释、规范性文件、内部规定
重点: 检察院相关司法解释和规范性文件

注意: 页面可能需要 JavaScript 渲染，优先使用 httpx，
若失败则回退到 Playwright。
"""

import re
import json
from pathlib import Path
from typing import List, Optional

from bs4 import BeautifulSoup
from loguru import logger

from .base_collector import BaseCollector, ParsedDocument


class SppCollector(BaseCollector):
    """最高人民检察院法律法规库采集器"""

    source_name = "spp-interpretations"
    knowledge_type = "interpretation"
    rate_limit = 4.0  # 较保守的限速

    BASE_URL = "https://www.spp.gov.cn"

    # 分类页面
    CATEGORIES = {
        "司法解释": "/spp/flfgk/sfjs/index.shtml",
        "规范性文件": "/spp/flfgk/gfxwj/index.shtml",
        "法律": "/spp/flfgk/fl/index.shtml",
    }

    async def download(self) -> List[Path]:
        """爬取最高检法规库"""
        all_items = []

        for category_name, category_path in self.CATEGORIES.items():
            self._report_progress(
                "download",
                f"正在爬取最高检{category_name}...",
                int(20 + list(self.CATEGORIES.keys()).index(category_name) / len(self.CATEGORIES) * 50),
            )

            try:
                items = await self._crawl_category(category_name, category_path)
                all_items.extend(items)
            except Exception as e:
                logger.error(f"爬取{category_name}失败: {e}")
                continue

        if all_items:
            output_path = self.raw_dir / "spp_items_raw.json"
            output_path.write_text(
                json.dumps(all_items, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(f"共爬取 {len(all_items)} 条记录")
            return [output_path]

        return []

    async def _crawl_category(
        self, category_name: str, category_path: str
    ) -> List[dict]:
        """爬取分类页面"""
        items = []
        page = 0
        max_pages = 30

        while page < max_pages:
            if page == 0:
                url = f"{self.BASE_URL}{category_path}"
            else:
                # spp.gov.cn 的分页通常是 index_1.shtml, index_2.shtml
                base = category_path.replace("index.shtml", "")
                url = f"{self.BASE_URL}{base}index_{page}.shtml"

            try:
                resp = await self._request_with_retry("GET", url)
                if resp.status_code == 404:
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                page_items = self._extract_list_items(soup, category_name)

                if not page_items:
                    break

                # 对每个条目获取详情
                for item in page_items:
                    detail_url = item.get("url", "")
                    if detail_url and not detail_url.startswith("http"):
                        detail_url = f"{self.BASE_URL}{detail_url}"

                    if detail_url:
                        try:
                            detail = await self._crawl_detail(detail_url)
                            if detail:
                                detail["category"] = category_name
                                detail["title"] = detail.get("title") or item.get("title", "")
                                items.append(detail)
                        except Exception as e:
                            logger.debug(f"获取详情失败 {detail_url}: {e}")
                            items.append({
                                "title": item.get("title", ""),
                                "url": detail_url,
                                "content": "",
                                "category": category_name,
                                "date": item.get("date", ""),
                            })

                page += 1

            except Exception as e:
                logger.warning(f"爬取{category_name}第{page}页失败: {e}")
                break

        return items

    async def _crawl_detail(self, url: str) -> Optional[dict]:
        """爬取文档详情"""
        resp = await self._request_with_retry("GET", url)
        soup = BeautifulSoup(resp.text, "html.parser")

        title = ""
        content = ""
        publish_date = ""

        # 标题
        title_el = soup.find("h1") or soup.find("h2") or soup.find("div", class_=re.compile(r"title"))
        if title_el:
            title = title_el.get_text(strip=True)

        # 正文
        content_el = (
            soup.find("div", class_=re.compile(r"content|article|detail|TRS_Editor", re.I))
            or soup.find("div", id=re.compile(r"content|article|zoom", re.I))
            or soup.find("article")
        )
        if content_el:
            for tag in content_el.find_all(["script", "style"]):
                tag.decompose()
            content = content_el.get_text(separator="\n", strip=True)

        # 日期
        page_text = soup.get_text()
        date_match = re.search(r"(\d{4}[-年/]\d{1,2}[-月/]\d{1,2})", page_text)
        if date_match:
            publish_date = date_match.group(1)

        if not title and not content:
            return None

        return {
            "title": title,
            "content": content,
            "url": url,
            "publish_date": publish_date,
            "issuing_authority": "最高人民检察院",
        }

    def _extract_list_items(self, soup: BeautifulSoup, category: str) -> List[dict]:
        """提取列表条目"""
        items = []

        # spp.gov.cn 的列表通常在 <ul class="list"> 或 <div class="list">
        containers = (
            soup.find_all("ul", class_=re.compile(r"list"))
            or soup.find_all("div", class_=re.compile(r"list"))
            or [soup]
        )

        for container in containers:
            for a in container.find_all("a"):
                href = a.get("href", "")
                text = a.get_text(strip=True)

                if not text or len(text) < 4 or not href:
                    continue
                if href == "#" or "javascript" in href.lower():
                    continue

                # 查找日期
                parent = a.parent
                date = ""
                if parent:
                    span = parent.find("span") or parent.find("em")
                    if span:
                        date_match = re.search(r"(\d{4}[-./]\d{1,2}[-./]\d{1,2})", span.get_text())
                        if date_match:
                            date = date_match.group(1)

                items.append({"title": text, "url": href, "date": date})

        return items

    async def parse(self, downloaded_files: List[Path]) -> List[ParsedDocument]:
        """解析爬取结果"""
        documents = []

        for file_path in downloaded_files:
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    continue

                for item in data:
                    doc = self._parse_spp_item(item)
                    if doc:
                        documents.append(doc)
            except Exception as e:
                logger.warning(f"解析失败 {file_path}: {e}")

        logger.info(f"共解析出 {len(documents)} 条检察院法规")
        return documents

    def _parse_spp_item(self, item: dict) -> Optional[ParsedDocument]:
        """解析单条记录"""
        title = item.get("title", "").strip()
        content = item.get("content", "").strip()

        if not title:
            return None
        if not content:
            content = f"《{title}》\n\n（全文内容待补充）"

        doc_id = f"spp_{self.content_hash(title)[:16]}"
        category = item.get("category", "司法解释")

        # 确定知识类型
        if "司法解释" in category or "解释" in title:
            kt = "interpretation"
        elif "规范" in category:
            kt = "compliance"
        else:
            kt = "law"

        cross_refs = self.extract_cross_references(content)

        return ParsedDocument(
            doc_id=doc_id,
            title=title,
            content=content,
            source="最高人民检察院法律法规库",
            source_url=item.get("url", ""),
            knowledge_type=kt,
            law_category=category,
            effective_date=item.get("publish_date", ""),
            issuing_authority=item.get("issuing_authority", "最高人民检察院"),
            tags=[category, "检察院"],
            cross_references=cross_refs,
        )
