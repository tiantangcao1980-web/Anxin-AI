# -*- coding: utf-8 -*-
"""
司法部行政法规库采集器

数据源: https://xzfg.moj.gov.cn/search2.html
内容: 611部现行有效行政法规
分类: 农业、环保、标准化、建设、水利等领域
"""

import re
import json
from pathlib import Path
from typing import List, Optional

from bs4 import BeautifulSoup
from loguru import logger

from .base_collector import BaseCollector, ParsedDocument


class AdminRegulationCollector(BaseCollector):
    """司法部行政法规库采集器"""

    source_name = "admin-regulations"
    knowledge_type = "regulation"
    rate_limit = 3.0

    BASE_URL = "https://xzfg.moj.gov.cn"
    SEARCH_URL = "https://xzfg.moj.gov.cn/search2.html"

    async def download(self) -> List[Path]:
        """爬取行政法规列表和全文"""
        all_regulations = []

        # 遍历分页
        page = 1
        max_pages = 80  # 611部 / ~10每页 ≈ 62页
        consecutive_empty = 0

        while page <= max_pages and consecutive_empty < 3:
            self._report_progress(
                "download",
                f"正在爬取行政法规列表 (第{page}页)...",
                int(10 + page / max_pages * 50),
            )

            try:
                url = f"{self.SEARCH_URL}?page={page}"
                resp = await self._request_with_retry("GET", url)
                soup = BeautifulSoup(resp.text, "html.parser")

                items = self._extract_regulation_list(soup)
                if not items:
                    consecutive_empty += 1
                    page += 1
                    continue

                consecutive_empty = 0

                for item in items:
                    detail_url = item.get("url", "")
                    if detail_url and not detail_url.startswith("http"):
                        detail_url = f"{self.BASE_URL}{detail_url}"

                    if detail_url:
                        try:
                            detail = await self._crawl_regulation_detail(detail_url)
                            if detail:
                                detail.update({
                                    "title": item.get("title", detail.get("title", "")),
                                    "list_date": item.get("date", ""),
                                })
                                all_regulations.append(detail)
                        except Exception as e:
                            logger.warning(f"爬取详情失败 {detail_url}: {e}")
                            # 仍记录基本信息
                            all_regulations.append({
                                "title": item.get("title", ""),
                                "url": detail_url,
                                "content": "",
                                "publish_date": item.get("date", ""),
                            })

                page += 1

            except Exception as e:
                logger.error(f"爬取列表页 {page} 失败: {e}")
                page += 1
                continue

        # 保存
        if all_regulations:
            output_path = self.raw_dir / "admin_regulations_raw.json"
            output_path.write_text(
                json.dumps(all_regulations, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(f"共爬取 {len(all_regulations)} 部行政法规")
            return [output_path]

        return []

    async def _crawl_regulation_detail(self, url: str) -> Optional[dict]:
        """爬取法规详情页"""
        resp = await self._request_with_retry("GET", url)
        soup = BeautifulSoup(resp.text, "html.parser")

        title = ""
        content = ""
        publish_date = ""
        authority = ""
        effective_date = ""

        # 标题
        title_el = (
            soup.find("h1")
            or soup.find("h2")
            or soup.find("div", class_=re.compile(r"title"))
        )
        if title_el:
            title = title_el.get_text(strip=True)

        # 正文
        content_el = (
            soup.find("div", class_=re.compile(r"content|article|law-content|detail", re.I))
            or soup.find("div", id=re.compile(r"content|article", re.I))
            or soup.find("article")
        )
        if content_el:
            # 去除脚本和样式
            for tag in content_el.find_all(["script", "style"]):
                tag.decompose()
            content = content_el.get_text(separator="\n", strip=True)

        # 元数据提取
        meta_text = soup.get_text()

        # 发布日期
        for pattern in [
            r"公布日期[：:]\s*(\d{4}[-./年]\d{1,2}[-./月]\d{1,2})",
            r"发布日期[：:]\s*(\d{4}[-./年]\d{1,2}[-./月]\d{1,2})",
            r"(\d{4}年\d{1,2}月\d{1,2}日).{0,10}公布",
        ]:
            match = re.search(pattern, meta_text)
            if match:
                publish_date = match.group(1)
                break

        # 施行日期
        for pattern in [
            r"施行日期[：:]\s*(\d{4}[-./年]\d{1,2}[-./月]\d{1,2})",
            r"自(\d{4}年\d{1,2}月\d{1,2}日)起施行",
        ]:
            match = re.search(pattern, meta_text)
            if match:
                effective_date = match.group(1)
                break

        # 发布机关
        for pattern in [
            r"制定机关[：:]\s*(.+?)(?:\n|$)",
            r"发布机关[：:]\s*(.+?)(?:\n|$)",
        ]:
            match = re.search(pattern, meta_text)
            if match:
                authority = match.group(1).strip()
                break

        if not authority:
            authority = "国务院"  # 行政法规默认由国务院发布

        return {
            "title": title,
            "content": content,
            "url": url,
            "publish_date": publish_date,
            "effective_date": effective_date,
            "issuing_authority": authority,
        }

    def _extract_regulation_list(self, soup: BeautifulSoup) -> List[dict]:
        """从列表页提取法规条目"""
        items = []

        # 通用提取策略
        for a in soup.find_all("a"):
            href = a.get("href", "")
            text = a.get_text(strip=True)

            # 过滤非法规链接
            if not text or len(text) < 4:
                continue
            if not href or href == "#":
                continue
            if "javascript" in href.lower():
                continue

            # 包含"条例"/"办法"/"规定"等关键词或匹配法规详情页模式
            is_regulation = any(
                kw in text
                for kw in ["条例", "办法", "规定", "规则", "细则", "暂行", "实施"]
            ) or re.search(r"/[A-Za-z0-9]+\.html", href)

            if is_regulation:
                # 查找同级日期
                parent = a.parent
                date = ""
                if parent:
                    date_match = re.search(
                        r"(\d{4}[-./]\d{1,2}[-./]\d{1,2})",
                        parent.get_text(),
                    )
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
                    doc = self._parse_regulation(item)
                    if doc:
                        documents.append(doc)
            except Exception as e:
                logger.warning(f"解析文件 {file_path} 失败: {e}")

        logger.info(f"共解析出 {len(documents)} 部行政法规")
        return documents

    def _parse_regulation(self, item: dict) -> Optional[ParsedDocument]:
        """解析单部行政法规"""
        title = item.get("title", "").strip()
        content = item.get("content", "").strip()

        if not title:
            return None
        # 允许content为空（某些情况下只有标题和元数据）
        if not content:
            content = f"《{title}》\n\n（全文内容待补充）"

        doc_id = f"ar_{self.content_hash(title)[:16]}"

        effective_date = item.get("effective_date", "") or item.get("publish_date", "")

        # 提取交叉引用
        cross_refs = self.extract_cross_references(content) if content else []

        # 领域标签
        tags = ["行政法规"]
        domain_keywords = {
            "农业": "农业", "环境": "环保", "建设": "建设", "水利": "水利",
            "交通": "交通", "教育": "教育", "卫生": "卫生", "安全": "安全",
            "土地": "土地", "税": "税务", "金融": "金融", "海关": "海关",
            "劳动": "劳动", "工商": "工商", "质量": "质量", "标准": "标准化",
        }
        for kw, tag in domain_keywords.items():
            if kw in title:
                tags.append(tag)

        return ParsedDocument(
            doc_id=doc_id,
            title=title,
            content=content,
            source="司法部行政法规库",
            source_url=item.get("url", ""),
            knowledge_type="regulation",
            law_category="行政法规",
            effective_date=effective_date,
            issuing_authority=item.get("issuing_authority", "国务院"),
            tags=tags,
            cross_references=cross_refs,
        )
