# -*- coding: utf-8 -*-
"""
合同示范文本库采集器

数据源: https://htsfwb.samr.gov.cn/
内容: 国家和地方各部门发布的合同示范文本
分类: 生活消费、农业资源、经营活动、工程建设等五大类

对中小企业客户价值最高的数据源之一。
"""

import re
from pathlib import Path
from typing import List, Optional

from bs4 import BeautifulSoup
from loguru import logger

from .base_collector import BaseCollector, ParsedDocument


class ContractTemplateCollector(BaseCollector):
    """合同示范文本库采集器"""

    source_name = "contract-templates"
    knowledge_type = "template"
    rate_limit = 3.0  # 保守限速

    BASE_URL = "https://htsfwb.samr.gov.cn"

    # 合同分类及其URL路径
    CATEGORIES = {
        "生活消费": "/Consume",
        "农业资源": "/Agriculture",
        "经营活动": "/Business",
        "工程建设": "/Construction",
        "其他": "/Other",
    }

    async def download(self) -> List[Path]:
        """爬取合同模板列表和详情页"""
        all_pages = []

        for category_name, category_path in self.CATEGORIES.items():
            self._report_progress(
                "download", f"正在爬取分类: {category_name}", 20
            )

            try:
                templates = await self._crawl_category(
                    category_name, category_path
                )
                all_pages.extend(templates)
            except Exception as e:
                logger.error(f"爬取分类 {category_name} 失败: {e}")
                continue

        # 保存爬取结果
        if all_pages:
            import json
            output_path = self.raw_dir / "templates_raw.json"
            output_path.write_text(
                json.dumps(all_pages, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(f"共爬取 {len(all_pages)} 个合同模板")
            return [output_path]

        return []

    async def _crawl_category(
        self, category_name: str, category_path: str
    ) -> List[dict]:
        """爬取某个分类下的所有合同模板"""
        templates = []
        page = 1
        max_pages = 50  # 安全上限

        while page <= max_pages:
            url = f"{self.BASE_URL}{category_path}?page={page}"
            try:
                resp = await self._request_with_retry("GET", url)
                soup = BeautifulSoup(resp.text, "html.parser")

                # 查找模板列表项
                items = self._extract_list_items(soup)
                if not items:
                    break

                for item in items:
                    detail_url = item.get("url", "")
                    if detail_url and not detail_url.startswith("http"):
                        detail_url = f"{self.BASE_URL}{detail_url}"

                    # 爬取详情页
                    if detail_url:
                        try:
                            detail = await self._crawl_detail(detail_url)
                            if detail:
                                detail["category"] = category_name
                                detail["list_url"] = url
                                templates.append(detail)
                        except Exception as e:
                            logger.warning(f"爬取详情失败 {detail_url}: {e}")
                    else:
                        templates.append({
                            "title": item.get("title", ""),
                            "category": category_name,
                            "content": item.get("summary", ""),
                            "url": url,
                            "publish_date": item.get("date", ""),
                            "issuing_authority": item.get("authority", ""),
                        })

                # 检查是否有下一页
                if not self._has_next_page(soup):
                    break
                page += 1

            except Exception as e:
                logger.warning(f"爬取列表页 {url} 失败: {e}")
                break

        return templates

    async def _crawl_detail(self, url: str) -> Optional[dict]:
        """爬取合同模板详情页"""
        resp = await self._request_with_retry("GET", url)
        soup = BeautifulSoup(resp.text, "html.parser")

        title = ""
        content = ""
        publish_date = ""
        authority = ""

        # 提取标题
        title_el = soup.find("h1") or soup.find("h2") or soup.find("title")
        if title_el:
            title = title_el.get_text(strip=True)

        # 提取正文内容
        # 合同示范文本库通常有一个主内容区
        content_candidates = [
            soup.find("div", class_=re.compile(r"content|article|detail|body", re.I)),
            soup.find("div", id=re.compile(r"content|article|detail|body", re.I)),
            soup.find("article"),
            soup.find("div", class_="main"),
        ]

        for candidate in content_candidates:
            if candidate:
                content = candidate.get_text(separator="\n", strip=True)
                if len(content) > 50:  # 至少50个字符才算有效内容
                    break

        # 如果还是没找到内容，取整个body
        if not content or len(content) < 50:
            body = soup.find("body")
            if body:
                # 去除脚本和样式
                for tag in body.find_all(["script", "style", "nav", "header", "footer"]):
                    tag.decompose()
                content = body.get_text(separator="\n", strip=True)

        # 提取发布日期和发布机关
        meta_text = soup.get_text()
        date_match = re.search(r"(\d{4}[-年]\d{1,2}[-月]\d{1,2})", meta_text)
        if date_match:
            publish_date = date_match.group(1).replace("年", "-").replace("月", "-").replace("日", "")

        auth_patterns = [
            r"发布(?:单位|机关|部门)[：:]\s*(.+?)(?:\n|$)",
            r"制定(?:单位|机关)[：:]\s*(.+?)(?:\n|$)",
        ]
        for pattern in auth_patterns:
            match = re.search(pattern, meta_text)
            if match:
                authority = match.group(1).strip()
                break

        if not title or not content:
            return None

        return {
            "title": title,
            "content": content,
            "url": url,
            "publish_date": publish_date,
            "issuing_authority": authority,
        }

    def _extract_list_items(self, soup: BeautifulSoup) -> List[dict]:
        """从列表页提取模板条目"""
        items = []

        # 尝试多种列表结构
        # 结构1: <ul><li><a>标题</a></li></ul>
        for li in soup.find_all("li"):
            a = li.find("a")
            if a and a.get("href"):
                title = a.get_text(strip=True)
                if title and len(title) > 3:
                    href = a.get("href", "")
                    date_span = li.find("span", class_=re.compile(r"date|time"))
                    items.append({
                        "title": title,
                        "url": href,
                        "date": date_span.get_text(strip=True) if date_span else "",
                    })

        # 结构2: <table><tr><td><a>标题</a></td></tr></table>
        if not items:
            for tr in soup.find_all("tr"):
                a = tr.find("a")
                if a and a.get("href"):
                    title = a.get_text(strip=True)
                    if title and len(title) > 3:
                        items.append({
                            "title": title,
                            "url": a.get("href", ""),
                        })

        # 结构3: <div class="item"><a>标题</a></div>
        if not items:
            for div in soup.find_all("div", class_=re.compile(r"item|list-item|card")):
                a = div.find("a")
                if a and a.get("href"):
                    title = a.get_text(strip=True)
                    if title and len(title) > 3:
                        items.append({
                            "title": title,
                            "url": a.get("href", ""),
                            "summary": div.get_text(strip=True)[:200],
                        })

        return items

    def _has_next_page(self, soup: BeautifulSoup) -> bool:
        """检查是否有下一页"""
        next_link = soup.find("a", string=re.compile(r"下一页|>|›|Next"))
        if next_link:
            href = next_link.get("href", "")
            if href and href != "#" and "javascript" not in href.lower():
                return True
        return False

    async def parse(self, downloaded_files: List[Path]) -> List[ParsedDocument]:
        """解析爬取结果"""
        import json

        documents = []

        for file_path in downloaded_files:
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    continue

                for item in data:
                    doc = self._parse_template_item(item)
                    if doc:
                        documents.append(doc)

            except Exception as e:
                logger.warning(f"解析文件 {file_path} 失败: {e}")

        logger.info(f"共解析出 {len(documents)} 个合同模板")
        return documents

    def _parse_template_item(self, item: dict) -> Optional[ParsedDocument]:
        """解析单个合同模板"""
        title = item.get("title", "").strip()
        content = item.get("content", "").strip()

        if not title or not content or len(content) < 30:
            return None

        doc_id = f"ct_{self.content_hash(title)[:16]}"

        # 根据标题判断合同子类型
        tags = [item.get("category", "")]
        sub_type_keywords = {
            "买卖": "买卖合同",
            "销售": "买卖合同",
            "采购": "买卖合同",
            "租赁": "租赁合同",
            "房屋": "房屋租赁",
            "劳动": "劳动合同",
            "劳务": "劳务合同",
            "服务": "服务合同",
            "委托": "委托合同",
            "加工": "加工合同",
            "承揽": "承揽合同",
            "运输": "运输合同",
            "保管": "保管合同",
            "仓储": "仓储合同",
            "借款": "借款合同",
            "融资": "融资合同",
            "保险": "保险合同",
            "技术": "技术合同",
            "知识产权": "知识产权",
            "建设": "建设工程",
            "施工": "建设工程",
            "设计": "设计合同",
            "物业": "物业管理",
            "供电": "供用电合同",
            "供水": "供用水合同",
            "特许经营": "特许经营",
            "合伙": "合伙协议",
            "股权": "股权协议",
        }
        for keyword, tag in sub_type_keywords.items():
            if keyword in title:
                tags.append(tag)
                break

        return ParsedDocument(
            doc_id=doc_id,
            title=title,
            content=content,
            source="国家市场监督管理总局合同示范文本库",
            source_url=item.get("url", ""),
            knowledge_type="template",
            law_category=item.get("category", ""),
            effective_date=item.get("publish_date", ""),
            issuing_authority=item.get("issuing_authority", "国家市场监督管理总局"),
            tags=[t for t in tags if t],
            extra_metadata={
                "template_type": "contract",
                "list_url": item.get("list_url", ""),
            },
        )
