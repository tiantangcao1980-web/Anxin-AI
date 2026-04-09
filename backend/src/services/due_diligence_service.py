"""
尽职调查服务

提供企业信息聚合、风险评估、诉讼查询等功能。

数据源:
  - 天眼查/企查查/爱企查: 工商信息
  - 中国执行信息公开网 (zxgk.court.gov.cn): 被执行人 + 失信名单
  - 信用中国 (creditchina.gov.cn): 行政处罚、信用信息
  - 中国裁判文书网 (wenshu.court.gov.cn): 裁判文书（受限）
  - LLM: 风险评估与分析补充

安全机制:
  - 基于用户ID的查询频率限制（防止恶意爬取）
  - 单用户每日/每小时查询上限
  - 查询日志审计
"""

import asyncio
import json
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger

from src.core.config import settings


# ==================== 查询频率限制器 ====================


class InvestigationRateLimiter:
    """
    调查查询频率限制器

    防止用户恶意高频查询外部数据源，保护系统和数据源安全。
    基于内存计数，进程重启后重置（可后续扩展为 Redis 存储）。
    """

    # 默认限制（可通过 settings 覆盖）
    MAX_QUERIES_PER_HOUR = 20      # 每用户每小时最大查询数
    MAX_QUERIES_PER_DAY = 50       # 每用户每天最大查询数
    MAX_SAME_COMPANY_PER_HOUR = 5  # 同一企业每小时最大查询数
    GLOBAL_MAX_PER_MINUTE = 10     # 全局每分钟最大查询数（保护外部数据源）

    def __init__(self):
        # {user_id: [(timestamp, company_name), ...]}
        self._user_queries: Dict[str, list] = defaultdict(list)
        # [(timestamp, company_name), ...]
        self._global_queries: list = []
        # {user_id: block_until_timestamp}
        self._blocked_users: Dict[str, float] = {}

    def check_and_record(
        self, user_id: str, company_name: str
    ) -> Dict[str, Any]:
        """
        检查查询是否允许，并记录。

        Returns:
            {"allowed": bool, "reason": str, "remaining_hour": int, "remaining_day": int}
        """
        now = time.time()
        hour_ago = now - 3600
        day_ago = now - 86400
        minute_ago = now - 60

        # 检查是否被临时封禁
        if user_id in self._blocked_users:
            if now < self._blocked_users[user_id]:
                remaining = int(self._blocked_users[user_id] - now)
                return {
                    "allowed": False,
                    "reason": f"查询过于频繁，请 {remaining} 秒后重试",
                    "remaining_hour": 0,
                    "remaining_day": 0,
                }
            else:
                del self._blocked_users[user_id]

        # 清理过期记录
        self._user_queries[user_id] = [
            (ts, cn) for ts, cn in self._user_queries[user_id] if ts > day_ago
        ]
        self._global_queries = [
            (ts, cn) for ts, cn in self._global_queries if ts > minute_ago
        ]

        user_history = self._user_queries[user_id]

        # 检查全局限速
        if len(self._global_queries) >= self.GLOBAL_MAX_PER_MINUTE:
            return {
                "allowed": False,
                "reason": "系统繁忙，请稍后重试",
                "remaining_hour": 0,
                "remaining_day": 0,
            }

        # 检查每小时限制
        hour_count = sum(1 for ts, _ in user_history if ts > hour_ago)
        if hour_count >= self.MAX_QUERIES_PER_HOUR:
            # 触发限速，临时封禁10分钟
            self._blocked_users[user_id] = now + 600
            logger.warning(f"用户 {user_id} 触发小时查询限制 ({hour_count}/{self.MAX_QUERIES_PER_HOUR})")
            return {
                "allowed": False,
                "reason": f"每小时查询上限为 {self.MAX_QUERIES_PER_HOUR} 次，请10分钟后重试",
                "remaining_hour": 0,
                "remaining_day": max(0, self.MAX_QUERIES_PER_DAY - len(user_history)),
            }

        # 检查每天限制
        if len(user_history) >= self.MAX_QUERIES_PER_DAY:
            logger.warning(f"用户 {user_id} 触发每日查询限制 ({len(user_history)}/{self.MAX_QUERIES_PER_DAY})")
            return {
                "allowed": False,
                "reason": f"每日查询上限为 {self.MAX_QUERIES_PER_DAY} 次，请明天再试",
                "remaining_hour": 0,
                "remaining_day": 0,
            }

        # 检查同一企业重复查询
        same_company_hour = sum(
            1 for ts, cn in user_history if ts > hour_ago and cn == company_name
        )
        if same_company_hour >= self.MAX_SAME_COMPANY_PER_HOUR:
            return {
                "allowed": False,
                "reason": f"同一企业每小时最多查询 {self.MAX_SAME_COMPANY_PER_HOUR} 次",
                "remaining_hour": max(0, self.MAX_QUERIES_PER_HOUR - hour_count),
                "remaining_day": max(0, self.MAX_QUERIES_PER_DAY - len(user_history)),
            }

        # 通过检查，记录查询
        self._user_queries[user_id].append((now, company_name))
        self._global_queries.append((now, company_name))

        return {
            "allowed": True,
            "reason": "",
            "remaining_hour": max(0, self.MAX_QUERIES_PER_HOUR - hour_count - 1),
            "remaining_day": max(0, self.MAX_QUERIES_PER_DAY - len(user_history)),
        }

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户查询统计"""
        now = time.time()
        history = self._user_queries.get(user_id, [])
        hour_count = sum(1 for ts, _ in history if ts > now - 3600)
        day_count = sum(1 for ts, _ in history if ts > now - 86400)
        return {
            "queries_this_hour": hour_count,
            "queries_today": day_count,
            "remaining_hour": max(0, self.MAX_QUERIES_PER_HOUR - hour_count),
            "remaining_day": max(0, self.MAX_QUERIES_PER_DAY - day_count),
            "is_blocked": user_id in self._blocked_users,
        }


# 全局单例
_rate_limiter = InvestigationRateLimiter()


_DUE_DILIGENCE_QUERY_PATTERNS = [
    re.compile(r"(尽职调查|尽调|背景调查|企业调查|公司调查)"),
    re.compile(r"(调查|查一下|查下|查查|看看|核查|评估|分析).{0,8}(公司|企业|供应商|合作方|交易对手|对方主体|对方)"),
    re.compile(r"(工商信息|股权结构|诉讼记录|失信记录|经营异常|行政处罚|信用记录|关联企业|关联关系)"),
    re.compile(r"(供应商|合作方|交易对手).{0,12}(可靠|靠谱|风险|背景|信用)"),
]

_COMPANY_NAME_PATTERNS = [
    re.compile(r"([A-Za-z0-9\u4e00-\u9fa5（）()·\-.]{2,60}?(?:有限责任公司|股份有限公司|集团有限公司|有限公司|集团|公司|企业))"),
]

_COMPANY_PLACEHOLDERS = {
    "一家公司", "一间公司", "一家企业", "一间企业", "这个公司", "这家公司",
    "那个公司", "那家公司", "某公司", "某企业", "目标公司", "合作公司",
    "合作企业", "供应商公司", "企业公司", "公司", "企业", "对方公司", "对方企业",
}

_KNOWN_COMPANY_ALIASES = (
    "腾讯", "阿里巴巴", "阿里", "字节跳动", "京东", "百度", "美团", "拼多多", "小米", "华为",
)

_LEADING_REQUEST_PREFIX = re.compile(
    r"^(请|麻烦|帮我|帮忙|想|我要|我想|请帮我)?"
    r"(调查一下|调查|查一下|查下|查查|查一查|看看|看下|核查|评估|分析|了解一下)?"
)


def detect_company_due_diligence_request(message: str) -> Dict[str, Any]:
    """
    检测用户是否在发起“公司/企业调查”请求，并尽量提取目标公司名称。

    Returns:
        {
            "matched": bool,
            "company_name": Optional[str],
            "reason": str,
        }
    """
    text = (message or "").strip()
    if not text:
        return {"matched": False, "company_name": None, "reason": "empty"}

    if "公司法" in text and not any(pattern.search(text) for pattern in _DUE_DILIGENCE_QUERY_PATTERNS[:2]):
        return {"matched": False, "company_name": None, "reason": "company_law_question"}

    matched_pattern = next((pattern.pattern for pattern in _DUE_DILIGENCE_QUERY_PATTERNS if pattern.search(text)), None)
    if not matched_pattern:
        return {"matched": False, "company_name": None, "reason": "no_due_diligence_signal"}

    company_name = extract_company_name_from_text(text)
    return {
        "matched": True,
        "company_name": company_name,
        "reason": f"matched:{matched_pattern}",
    }


def extract_company_name_from_text(text: str) -> Optional[str]:
    """从用户输入中提取目标企业名称。"""
    if not text:
        return None

    normalized_text = _normalize_company_extraction_text(text)

    for pattern in _COMPANY_NAME_PATTERNS:
        matches = pattern.findall(normalized_text)
        if not matches:
            continue

        candidates = sorted(
            {_clean_company_candidate(match) for match in matches},
            key=len,
            reverse=True,
        )
        for candidate in candidates:
            if _is_valid_company_candidate(candidate):
                return candidate

    for alias in _KNOWN_COMPANY_ALIASES:
        if alias in normalized_text:
            return alias

    return None


def _is_valid_company_candidate(candidate: str) -> bool:
    """过滤明显不是企业名称的占位词和泛词。"""
    if not candidate or len(candidate) < 2:
        return False
    if candidate in _COMPANY_PLACEHOLDERS:
        return False
    if candidate.startswith(("这个", "这家", "那个", "那家", "某", "一家", "一间")):
        return False
    if candidate.endswith(("公司法", "企业法")):
        return False
    return True


def _normalize_company_extraction_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = _LEADING_REQUEST_PREFIX.sub("", cleaned).strip()
    return cleaned


def _clean_company_candidate(candidate: str) -> str:
    cleaned = candidate.strip("「」『』“”\"'：:，,。.？? ")
    cleaned = _LEADING_REQUEST_PREFIX.sub("", cleaned).strip()
    return cleaned


def format_due_diligence_chat_response(company_name: str, data: Dict[str, Any]) -> str:
    """将尽调结果格式化为适合聊天场景的结构化摘要。"""
    basic_info = data.get("basic_info", {}) or {}
    litigation = data.get("litigation", {}) or {}
    credit = data.get("credit", {}) or {}
    risk = data.get("risk", {}) or {}

    overall_rating = risk.get("overall_rating", "unknown")
    risk_labels = {
        "low": "低风险",
        "medium": "中风险",
        "high": "高风险",
        "critical": "重大风险",
        "unknown": "待核验",
    }
    overall_label = risk_labels.get(str(overall_rating).lower(), str(overall_rating))

    total_cases = int(litigation.get("plaintiff_cases", 0) or 0) + int(litigation.get("defendant_cases", 0) or 0)
    execution_cases = int(litigation.get("execution_cases", 0) or 0)
    dishonest_records = int(litigation.get("dishonest_records", 0) or 0)
    risk_points = [str(item).strip() for item in (risk.get("risk_points") or []) if str(item).strip()]
    recommendations = [str(item).strip() for item in (risk.get("recommendations") or []) if str(item).strip()]
    credit_rating = credit.get("credit_rating") or "待核验"
    data_source = basic_info.get("data_source") or "调查服务"

    summary_lines = [
        f"已识别为企业调查需求，以下是对“{company_name}”的尽调摘要：",
        "",
        "1. 企业概况",
        f"- 名称：{basic_info.get('name') or company_name}",
        f"- 经营状态：{basic_info.get('status') or '待核验'}",
        f"- 法定代表人：{basic_info.get('legal_representative') or '待核验'}",
        f"- 注册资本：{basic_info.get('registered_capital') or '待核验'}",
        f"- 成立日期：{basic_info.get('established_date') or '待核验'}",
        "",
        "2. 风险结论",
        f"- 综合风险等级：{overall_label}",
        f"- 诉讼相关案件数：{total_cases}",
        f"- 被执行案件数：{execution_cases}" + (f"（来源：中国执行信息公开网）" if execution_cases else ""),
        f"- 失信被执行人记录：{dishonest_records}" + (f"（来源：全国法院失信被执行人名单）" if dishonest_records else ""),
        f"- 信用评级：{credit_rating}",
        f"- 风险分项：经营 {risk.get('operation_risk', 'N/A')} / 诉讼 {risk.get('litigation_risk', 'N/A')} / 信用 {risk.get('credit_risk', 'N/A')} / 合规 {risk.get('compliance_risk', 'N/A')} / 关联 {risk.get('relation_risk', 'N/A')}",
        "",
        "3. 重点发现",
    ]

    if risk_points:
        summary_lines.extend([f"- {item}" for item in risk_points[:4]])
    else:
        summary_lines.append("- 暂未识别到明确高风险点，建议继续核验工商、诉讼与信用公开记录。")

    summary_lines.extend(["", "4. 建议动作"])
    if recommendations:
        summary_lines.extend([f"- {item}" for item in recommendations[:3]])
    else:
        summary_lines.extend([
            "- 补充核查最新工商登记与年报信息。",
            "- 重点核查涉诉、被执行和行政处罚记录。",
            "- 如用于交易或合作决策，建议进一步做股权穿透和实控人关联排查。",
        ])

    summary_lines.extend([
        "",
        f"说明：本次摘要的数据来源标记为“{data_source}”。若其中包含 AI 推断字段，请在正式决策前以工商、裁判文书、执行信息等公开记录再次核验。",
    ])

    return "\n".join(summary_lines)


class DueDiligenceService:
    """尽职调查服务"""

    def __init__(self):
        self._workforce = None
        self._llm_agent = None

    @property
    def workforce(self):
        """延迟导入 workforce，避免循环依赖"""
        if self._workforce is None:
            from src.agents.workforce import get_workforce
            self._workforce = get_workforce()
        return self._workforce

    @property
    def llm_agent(self):
        """获取一个轻量 Agent 实例，用于直接 LLM 调用（绕过 workforce 管道）"""
        if self._llm_agent is None:
            from src.agents.workforce import get_workforce
            wf = get_workforce()
            # 优先用尽职调查Agent，否则取任何可用 agent
            self._llm_agent = wf.agents.get("due_diligence") or wf.agents.get("legal_advisor")
            if not self._llm_agent and wf.agents:
                self._llm_agent = list(wf.agents.values())[0]
        return self._llm_agent

    async def _fetch_execution_info(self, company_name: str) -> Dict[str, Any]:
        """
        从中国执行信息公开网查询被执行人信息。

        数据源: https://zxgk.court.gov.cn/
        注意: 该网站有瑞数反爬保护，使用 Playwright 模拟浏览器查询。
        返回: {"execution_cases": int, "total_amount": str, "records": [...]}
        """
        result = {"execution_cases": 0, "total_amount": "", "records": [], "dishonest_records": 0}

        # 优先尝试 Crawl4AI（反检测能力更强）
        try:
            from src.services.crawl4ai_service import crawl4ai_service
            c4_result = await crawl4ai_service.crawl_url(
                f"https://zxgk.court.gov.cn/zhixing/?pName={company_name}",
                timeout=20,
            )
            if c4_result.get("success") and c4_result.get("content"):
                content = c4_result["content"]
                # 从 Markdown 内容中提取执行案件数
                import re
                case_matches = re.findall(r'(\d+)\s*(?:件|条|项)', content)
                if case_matches:
                    result["execution_cases"] = int(case_matches[0])
                    logger.info(f"Crawl4AI 获取执行信息成功: {company_name}, {result['execution_cases']} 件")
                    return result
        except Exception as c4e:
            logger.debug(f"Crawl4AI 执行信息获取失败: {c4e}")

        # Fallback: Playwright
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.debug("Playwright 未安装，跳过执行信息查询")
            return result

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 720},
                )
                page = await context.new_page()

                # === 1. 查询被执行人信息 ===
                try:
                    await page.goto("https://zxgk.court.gov.cn/zhixing/", timeout=15000)
                    await page.wait_for_load_state("networkidle", timeout=10000)

                    # 填写企业名称
                    name_input = page.locator('input[name="pName"], input#pName, input.input-txt').first
                    await name_input.fill(company_name)

                    # 点击搜索
                    search_btn = page.locator('button:has-text("搜索"), a:has-text("搜索"), .search-btn').first
                    await search_btn.click()
                    await page.wait_for_timeout(3000)

                    # 提取结果
                    content = await page.content()
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, "html.parser")

                    # 查找结果表格或列表
                    rows = soup.find_all("tr") or soup.find_all("div", class_=re.compile(r"result|item|record"))
                    records = []
                    for row in rows[1:11]:  # 最多取10条
                        cells = row.find_all("td") or row.find_all("span")
                        if len(cells) >= 3:
                            record = {
                                "case_no": cells[0].get_text(strip=True) if cells else "",
                                "court": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                                "amount": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                                "status": cells[-1].get_text(strip=True) if cells else "",
                            }
                            records.append(record)

                    result["execution_cases"] = len(records)
                    result["records"] = records
                    if records:
                        logger.info(f"执行信息查询成功: {company_name}, {len(records)} 条记录")

                except Exception as e:
                    logger.debug(f"被执行人查询失败: {e}")

                # === 2. 查询失信被执行人 ===
                try:
                    await page.goto("https://zxgk.court.gov.cn/shixin/", timeout=15000)
                    await page.wait_for_load_state("networkidle", timeout=10000)

                    name_input = page.locator('input[name="pName"], input#pName, input.input-txt').first
                    await name_input.fill(company_name)

                    search_btn = page.locator('button:has-text("搜索"), a:has-text("搜索"), .search-btn').first
                    await search_btn.click()
                    await page.wait_for_timeout(3000)

                    content = await page.content()
                    soup = BeautifulSoup(content, "html.parser")
                    rows = soup.find_all("tr") or soup.find_all("div", class_=re.compile(r"result|item"))
                    dishonest_count = max(0, len(rows) - 1)  # 减去表头
                    result["dishonest_records"] = dishonest_count

                    if dishonest_count > 0:
                        logger.info(f"失信查询成功: {company_name}, {dishonest_count} 条失信记录")

                except Exception as e:
                    logger.debug(f"失信被执行人查询失败: {e}")

                await browser.close()

        except Exception as e:
            logger.warning(f"执行信息查询整体失败: {e}")

        return result

    async def _fetch_credit_china_info(self, company_name: str) -> Dict[str, Any]:
        """
        从信用中国查询企业信用信息（Playwright 方式，绕过瑞数反爬）。

        数据源: https://www.creditchina.gov.cn/
        返回: {"penalties": int, "red_list": bool, "black_list": bool, "records": [...]}
        """
        result = {"penalties": 0, "red_list": False, "black_list": False, "records": []}

        # 优先尝试 Crawl4AI
        try:
            from src.services.crawl4ai_service import crawl4ai_service
            credit_url = f"https://www.creditchina.gov.cn/xinyongxinxixiangqing/xyDetail.html?searchState=1&entityType=1&keyword={company_name}"
            c4_result = await crawl4ai_service.crawl_url(credit_url, timeout=20)
            if c4_result.get("success") and c4_result.get("content"):
                content = c4_result["content"]
                import re
                # 提取行政处罚数
                penalty_match = re.findall(r'行政处罚[^0-9]*(\d+)', content)
                if penalty_match:
                    result["penalties"] = int(penalty_match[0])
                # 检测黑名单
                if "严重失信" in content or "黑名单" in content:
                    result["black_list"] = True
                if "守信红名单" in content or "红名单" in content:
                    result["red_list"] = True
                if result["penalties"] > 0 or result["black_list"]:
                    logger.info(f"Crawl4AI 信用中国数据成功: {company_name}, 处罚={result['penalties']}")
                    return result
        except Exception as c4e:
            logger.debug(f"Crawl4AI 信用中国获取失败: {c4e}")

        # Fallback: Playwright
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.debug("Playwright 未安装，跳过信用中国查询")
            return result

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                )
                page = await context.new_page()

                await page.goto(
                    f"https://www.creditchina.gov.cn/xinyongxinxixiangqing/xyDetail.html?searchState=1&entityType=1&keyword={company_name}",
                    timeout=20000,
                )
                await page.wait_for_timeout(3000)

                content = await page.content()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, "html.parser")

                # 提取行政处罚记录
                penalty_sections = soup.find_all(
                    string=re.compile(r"行政处罚|行政许可|经营异常")
                )
                for section in penalty_sections:
                    parent = section.find_parent("div")
                    if parent:
                        rows = parent.find_all("tr")
                        for row in rows[1:6]:  # 最多5条
                            cells = row.find_all("td")
                            if cells:
                                result["records"].append({
                                    "title": cells[0].get_text(strip=True) if cells else "",
                                    "type": "行政处罚",
                                    "date": cells[-1].get_text(strip=True) if cells else "",
                                })
                                result["penalties"] += 1

                # 检查黑名单
                page_text = soup.get_text()
                if "严重失信" in page_text or "黑名单" in page_text:
                    result["black_list"] = True
                if "守信红名单" in page_text:
                    result["red_list"] = True

                if result["penalties"] > 0 or result["black_list"]:
                    logger.info(
                        f"信用中国查询成功: {company_name}, "
                        f"{result['penalties']}条处罚, 黑名单={result['black_list']}"
                    )

                await browser.close()

        except Exception as e:
            logger.warning(f"信用中国查询失败: {e}")

        return result

    async def _fetch_wenshu_info(self, company_name: str) -> Dict[str, Any]:
        """
        从中国裁判文书网查询相关裁判文书（Playwright 方式）。

        数据源: https://wenshu.court.gov.cn/
        注意: 反爬极严格，仅做轻量查询（获取案件数量和摘要），
              不做批量爬取。若触发验证码则立即放弃。
        返回: {"case_count": int, "cases": [...], "source": str}
        """
        result = {"case_count": 0, "cases": [], "source": "中国裁判文书网"}

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.debug("Playwright 未安装，跳过裁判文书网查询")
            return result

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                )
                page = await context.new_page()

                # 访问搜索页
                await page.goto("https://wenshu.court.gov.cn/", timeout=15000)
                await page.wait_for_timeout(2000)

                # 检查是否有验证码
                content = await page.content()
                if "验证" in content and ("滑" in content or "captcha" in content.lower()):
                    logger.info("裁判文书网触发验证码，放弃查询")
                    await browser.close()
                    return result

                # 尝试搜索
                try:
                    search_input = page.locator('input[type="text"], input.search-input, #keyword').first
                    await search_input.fill(company_name)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(5000)

                    content = await page.content()
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, "html.parser")

                    # 尝试提取案件数量
                    count_el = soup.find(string=re.compile(r"共?\s*\d+\s*条"))
                    if count_el:
                        count_match = re.search(r"(\d+)", count_el)
                        if count_match:
                            result["case_count"] = int(count_match.group(1))

                    # 提取案件列表（最多5条摘要）
                    items = soup.find_all("div", class_=re.compile(r"result|item|case", re.I))
                    for item in items[:5]:
                        title = item.find("a")
                        if title:
                            result["cases"].append({
                                "title": title.get_text(strip=True)[:100],
                                "url": title.get("href", ""),
                            })

                    if result["case_count"] > 0:
                        logger.info(f"裁判文书网查询成功: {company_name}, {result['case_count']} 条文书")

                except Exception as e:
                    logger.debug(f"裁判文书网搜索失败: {e}")

                await browser.close()

        except Exception as e:
            logger.warning(f"裁判文书网查询失败: {e}")

        return result

    async def _fetch_real_company_data(self, company_name: str) -> Optional[Dict[str, Any]]:
        """
        从公开数据源抓取真实企业工商信息。
        尝试多个来源，返回第一个成功的结果。
        """
        import httpx

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        # --- 数据源 1: 尝试天眼查搜索建议接口 ---
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    "https://capi.tianyancha.com/cloud-tempest/search/suggest/v3",
                    params={"keyword": company_name},
                    headers={**headers, "Referer": "https://www.tianyancha.com/"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("data", [])
                    if items and isinstance(items, list):
                        for item in items:
                            if company_name in (item.get("comName", "") or item.get("name", "")):
                                result = {
                                    "name": item.get("comName") or item.get("name", company_name),
                                    "legal_representative": item.get("legalPersonName", ""),
                                    "registered_capital": item.get("regCapital", ""),
                                    "established_date": item.get("estiblishTime", ""),
                                    "address": item.get("regLocation", ""),
                                    "company_type": item.get("companyType", ""),
                                    "status": item.get("regStatus", "正常"),
                                    "business_scope": item.get("businessScope", ""),
                                    "credit_code": item.get("creditCode", ""),
                                }
                                logger.info(f"天眼查数据获取成功: {company_name}")
                                return result
        except Exception as e:
            logger.debug(f"天眼查接口不可用: {e}")

        # --- 数据源 2: 尝试企查查搜索接口 ---
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    "https://www.qcc.com/api/search/getQuickSearchResult",
                    params={"searchKey": company_name},
                    headers={**headers, "Referer": "https://www.qcc.com/"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("data", {}).get("list", []) if isinstance(data.get("data"), dict) else []
                    if items:
                        item = items[0]
                        result = {
                            "name": item.get("Name", company_name),
                            "legal_representative": item.get("OperName", ""),
                            "registered_capital": item.get("RegistCapi", ""),
                            "established_date": item.get("StartDate", ""),
                            "address": item.get("Address", ""),
                            "status": item.get("Status", "正常"),
                            "business_scope": item.get("Scope", ""),
                        }
                        logger.info(f"企查查数据获取成功: {company_name}")
                        return result
        except Exception as e:
            logger.debug(f"企查查接口不可用: {e}")

        # --- 数据源 3: 尝试爱企查搜索接口 ---
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    "https://aiqicha.baidu.com/s",
                    params={"q": company_name, "t": 0},
                    headers={**headers, "Referer": "https://aiqicha.baidu.com/"},
                )
                if resp.status_code == 200:
                    # 爱企查返回 HTML，尝试提取 JSON 数据
                    text = resp.text
                    # 搜索页面可能包含结构化数据
                    json_match = re.search(r'window\.pageData\s*=\s*(\{[\s\S]*?\});', text)
                    if json_match:
                        page_data = json.loads(json_match.group(1))
                        items = page_data.get("result", {}).get("resultList", [])
                        if items:
                            item = items[0]
                            result = {
                                "name": item.get("titleName", company_name),
                                "legal_representative": item.get("legalPerson", ""),
                                "registered_capital": item.get("regCapital", ""),
                                "established_date": item.get("startDate", ""),
                                "address": item.get("domicile", ""),
                                "status": item.get("openStatus", "正常"),
                                "business_scope": "",
                            }
                            logger.info(f"爱企查数据获取成功: {company_name}")
                            return result
        except Exception as e:
            logger.debug(f"爱企查接口不可用: {e}")

        # --- 数据源 4: 国家企业信用信息公示系统 (GSXT) ---
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                # GSXT 搜索接口
                resp = await client.post(
                    "https://www.gsxt.gov.cn/corp-query-entprise-info-searchent-search.html",
                    data={"searchword": company_name},
                    headers={
                        **headers,
                        "Referer": "https://www.gsxt.gov.cn/index.html",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        items = data.get("data", [])
                        if items and isinstance(items, list):
                            for item in items:
                                if company_name in str(item.get("entName", "")):
                                    result = {
                                        "name": item.get("entName", company_name),
                                        "legal_representative": item.get("leRepNm", ""),
                                        "registered_capital": item.get("regCap", ""),
                                        "established_date": item.get("estDate", ""),
                                        "address": item.get("dom", ""),
                                        "status": item.get("regState", "正常"),
                                        "unified_credit_code": item.get("uniscId", ""),
                                        "company_type": item.get("entType", ""),
                                    }
                                    logger.info(f"国家企业信用信息公示系统数据获取成功: {company_name}")
                                    return result
                    except (json.JSONDecodeError, KeyError):
                        pass
        except Exception as e:
            logger.debug(f"国家企业信用信息公示系统接口不可用: {e}")

        logger.warning(f"所有公开数据源均未获取到企业数据: {company_name}")
        return None

    async def quick_investigate(
        self,
        company_name: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        快速尽调 — 并行抓取多数据源，LLM 补充风险评估。

        数据源 (并行):
          1. 天眼查/企查查/爱企查 → 工商信息
          2. 执行信息公开网 → 被执行 + 失信
          3. 信用中国 → 行政处罚 + 黑名单
          4. 裁判文书网 → 相关案件（轻量查询）
          5. LLM → 风险分析

        安全: 基于 user_id 的查询频率限制
        """
        # ===== 频率限制检查 =====
        effective_user_id = user_id or "anonymous"
        rate_check = _rate_limiter.check_and_record(effective_user_id, company_name)
        if not rate_check["allowed"]:
            logger.warning(
                f"查询被限流: user={effective_user_id}, company={company_name}, "
                f"reason={rate_check['reason']}"
            )
            return {
                "error": rate_check["reason"],
                "rate_limited": True,
                "remaining_hour": rate_check["remaining_hour"],
                "remaining_day": rate_check["remaining_day"],
            }

        # 第一步：并行启动所有数据源
        real_data_task = asyncio.create_task(self._fetch_real_company_data(company_name))

        # 第二步：同时启动 LLM 调用做风险分析
        agent = self.llm_agent
        if not agent:
            raise Exception("无可用的 LLM Agent 实例")

        prompt = f"""请对企业「{company_name}」进行尽职调查风险分析，返回以下 JSON 数据。
重要：工商基本信息（法人、注册资本等）如果你不确定，请留空字符串""，不要编造。
注意：请直接返回合法 JSON，不要添加 markdown 代码块标记。

{{
  "basic_info": {{
    "name": "{company_name}",
    "legal_representative": "",
    "registered_capital": "",
    "established_date": "",
    "business_scope": "",
    "address": "",
    "company_type": "",
    "status": ""
  }},
  "litigation": {{
    "plaintiff_cases": 0,
    "defendant_cases": 0,
    "major_cases": [],
    "execution_cases": 0,
    "dishonest_records": 0,
    "risk_level": "low/medium/high"
  }},
  "credit": {{
    "administrative_penalties": 0,
    "tax_violations": 0,
    "environmental_penalties": 0,
    "abnormal_operations": 0,
    "serious_violations": 0,
    "credit_rating": "A/B/C/D"
  }},
  "risk": {{
    "operation_risk": 30,
    "litigation_risk": 20,
    "credit_risk": 25,
    "compliance_risk": 20,
    "relation_risk": 15,
    "overall_rating": "low/medium/high/critical",
    "risk_points": ["风险点1", "风险点2"],
    "recommendations": ["建议1", "建议2"]
  }}
}}

请基于你对该企业的了解填入数据。工商信息如果不确定请留空。风险评分和分析请合理评估。"""

        # 同时启动执行信息、信用中国、裁判文书网查询
        execution_task = asyncio.create_task(self._fetch_execution_info(company_name))
        credit_china_task = asyncio.create_task(self._fetch_credit_china_info(company_name))
        wenshu_task = asyncio.create_task(self._fetch_wenshu_info(company_name))

        logger.info(
            f"快速尽调 - 并行5源查询: 工商+执行+信用+文书+LLM | "
            f"user={effective_user_id}, company={company_name}, "
            f"剩余配额: {rate_check['remaining_hour']}/h, {rate_check['remaining_day']}/d"
        )
        response = await agent.chat(
            message=prompt,
            system_prompt_override=(
                "你是专业的企业尽职调查分析师。"
                "重要规则：工商基本信息（法人代表、注册资本、成立日期、地址）如果你不确定，必须留空字符串，绝对不要编造。"
                "风险评估和诉讼分析可以基于行业经验合理推测。"
                "请直接返回 JSON 格式数据，不要包含其他文字。"
            ),
        )

        # 解析 LLM 结果
        result = self._parse_quick_result(response, company_name)

        # 第三步：用真实工商数据覆盖 LLM 的 basic_info
        try:
            real_data = await asyncio.wait_for(real_data_task, timeout=5.0)
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"等待真实数据超时或失败: {e}")
            real_data = None

        if real_data:
            # 真实数据优先覆盖（只覆盖非空字段）
            basic = result.get("basic_info", {})
            for key, value in real_data.items():
                if value:  # 真实数据非空才覆盖
                    basic[key] = value
            basic["data_source"] = "公开工商数据"
            result["basic_info"] = basic
            logger.info(f"已用真实工商数据覆盖 LLM 数据: {company_name}")
        else:
            result["basic_info"]["data_source"] = "AI 分析（建议核实）"

        # 第四步：合并执行信息和信用中国数据
        try:
            execution_data = await asyncio.wait_for(execution_task, timeout=20.0)
            if execution_data:
                litigation = result.get("litigation", {})
                litigation["execution_cases"] = execution_data.get("execution_cases", 0)
                litigation["dishonest_records"] = execution_data.get("dishonest_records", 0)
                litigation["execution_records"] = execution_data.get("records", [])
                if execution_data.get("execution_cases", 0) > 0:
                    litigation["data_source_execution"] = "中国执行信息公开网"
                if execution_data.get("dishonest_records", 0) > 0:
                    litigation["data_source_dishonest"] = "全国法院失信被执行人名单"
                    # 有失信记录，提高诉讼风险评分
                    risk = result.get("risk", {})
                    risk["litigation_risk"] = max(risk.get("litigation_risk", 0), 70)
                    risk["risk_points"] = risk.get("risk_points", []) + [
                        f"存在 {execution_data['dishonest_records']} 条失信被执行人记录"
                    ]
                result["litigation"] = litigation
        except (asyncio.TimeoutError, Exception) as e:
            logger.debug(f"执行信息获取超时或失败: {e}")

        try:
            credit_china_data = await asyncio.wait_for(credit_china_task, timeout=25.0)
            if credit_china_data:
                credit = result.get("credit", {})
                credit["administrative_penalties"] = credit_china_data.get("penalties", 0)
                credit["credit_china_records"] = credit_china_data.get("records", [])
                if credit_china_data.get("penalties", 0) > 0:
                    credit["data_source_credit_china"] = "信用中国"
                if credit_china_data.get("black_list"):
                    risk = result.get("risk", {})
                    risk["credit_risk"] = max(risk.get("credit_risk", 0), 80)
                    risk["risk_points"] = risk.get("risk_points", []) + ["企业在信用中国黑名单中"]
                result["credit"] = credit
        except (asyncio.TimeoutError, Exception) as e:
            logger.debug(f"信用中国数据获取超时或失败: {e}")

        # 第六步：合并裁判文书网数据
        try:
            wenshu_data = await asyncio.wait_for(wenshu_task, timeout=25.0)
            if wenshu_data and wenshu_data.get("case_count", 0) > 0:
                litigation = result.get("litigation", {})
                litigation["wenshu_case_count"] = wenshu_data["case_count"]
                litigation["wenshu_cases"] = wenshu_data.get("cases", [])
                litigation["data_source_wenshu"] = "中国裁判文书网"
                result["litigation"] = litigation
                logger.info(f"裁判文书网: {company_name} 有 {wenshu_data['case_count']} 条相关文书")
        except (asyncio.TimeoutError, Exception) as e:
            logger.debug(f"裁判文书网数据获取超时或失败: {e}")

        # ===== 第七步：数据驱动风险重算 =====
        # 用真实采集的数据重新计算风险评分，替代 LLM 估算
        try:
            from src.services.risk_scoring_engine import risk_scoring_engine
            llm_risk = result.get("risk", {})  # 保留 LLM 结果作为补充
            data_driven_risk = risk_scoring_engine.compute_risk_scores(
                basic_info=result.get("basic_info", {}),
                litigation=result.get("litigation", {}),
                credit=result.get("credit", {}),
                llm_risk=llm_risk,
            )
            # 保留 LLM 的 risk_points（去重合并）
            existing_points = set(llm_risk.get("risk_points", []))
            new_points = data_driven_risk.get("risk_points", [])
            merged_points = list(existing_points | set(new_points))
            data_driven_risk["risk_points"] = merged_points[:15]

            # 保留 LLM 的 recommendations（去重合并）
            existing_recs = set(llm_risk.get("recommendations", []))
            new_recs = data_driven_risk.get("recommendations", [])
            data_driven_risk["recommendations"] = list(existing_recs | set(new_recs))[:10]

            result["risk"] = data_driven_risk
            logger.info(
                f"数据驱动风险评分: {company_name} "
                f"综合={data_driven_risk['overall_score']}, "
                f"质量={data_driven_risk['data_quality']}, "
                f"来源={data_driven_risk['data_sources']}"
            )
        except Exception as e:
            logger.warning(f"数据驱动风险评分失败，保留 LLM 评分: {e}")

        # 附加查询配额信息
        result["_query_quota"] = {
            "remaining_hour": rate_check["remaining_hour"],
            "remaining_day": rate_check["remaining_day"],
        }

        return result

    def _parse_quick_result(self, response: str, company_name: str) -> Dict[str, Any]:
        """解析快速尽调的 LLM 响应"""
        defaults = {
            "basic_info": {
                "name": company_name,
                "legal_representative": "",
                "registered_capital": "",
                "established_date": "",
                "business_scope": "",
                "address": "",
                "company_type": "",
                "status": "正常",
            },
            "litigation": {
                "plaintiff_cases": 0,
                "defendant_cases": 0,
                "major_cases": [],
                "execution_cases": 0,
                "dishonest_records": 0,
                "risk_level": "low",
            },
            "credit": {
                "administrative_penalties": 0,
                "tax_violations": 0,
                "environmental_penalties": 0,
                "abnormal_operations": 0,
                "serious_violations": 0,
                "credit_rating": "B",
            },
            "risk": {
                "operation_risk": 30,
                "litigation_risk": 20,
                "credit_risk": 25,
                "compliance_risk": 20,
                "relation_risk": 15,
                "overall_rating": "low",
                "risk_points": [],
                "recommendations": [],
            },
        }

        try:
            # 去掉 markdown 代码块标记
            cleaned = re.sub(r'```(?:json)?\s*', '', response).strip()
            cleaned = re.sub(r'```\s*$', '', cleaned).strip()

            # 尝试提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                parsed = json.loads(json_match.group())
                # 合并解析结果与默认值
                for key in defaults:
                    if key in parsed and isinstance(parsed[key], dict):
                        defaults[key] = {**defaults[key], **parsed[key]}
                return defaults
        except json.JSONDecodeError as e:
            logger.warning(f"快速尽调 JSON 解析失败: {e}")
        except Exception as e:
            logger.warning(f"快速尽调结果解析异常: {e}")

        return defaults
    
    async def investigate_company(
        self,
        company_name: str,
        investigation_type: str = "comprehensive",
    ) -> Dict[str, Any]:
        """
        企业综合调查
        
        Args:
            company_name: 企业名称
            investigation_type: 调查类型 (comprehensive/litigation/credit/basic)
        """
        logger.info(f"开始企业调查: {company_name}, 类型: {investigation_type}")
        
        # 根据调查类型确定需要执行的任务
        tasks = []
        
        if investigation_type in ["comprehensive", "basic"]:
            tasks.append(("basic_info", self._get_basic_info(company_name)))
        
        if investigation_type in ["comprehensive", "litigation"]:
            tasks.append(("litigation", self._get_litigation_info(company_name)))
        
        if investigation_type in ["comprehensive", "credit"]:
            tasks.append(("credit", self._get_credit_info(company_name)))
        
        if investigation_type == "comprehensive":
            tasks.append(("risk", self._assess_risks(company_name)))
            tasks.append(("relations", self._get_company_relations(company_name)))
        
        # 并行执行所有任务
        results = {}
        if tasks:
            task_results = await asyncio.gather(
                *[task[1] for task in tasks],
                return_exceptions=True
            )
            
            for (name, _), result in zip(tasks, task_results):
                if isinstance(result, Exception):
                    logger.error(f"任务 {name} 失败: {result}")
                    results[name] = {"error": str(result)}
                else:
                    results[name] = result
        
        # 生成综合报告
        report = await self._generate_report(company_name, results, investigation_type)
        
        return {
            "company_name": company_name,
            "investigation_type": investigation_type,
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "report": report,
        }
    
    async def _get_basic_info(self, company_name: str) -> Dict[str, Any]:
        """获取企业基本信息"""
        # 调用智能体获取信息
        result = await self.workforce.process_task(
            task_description=f"""请查询企业"{company_name}"的基本工商信息，包括：
1. 企业全称和曾用名
2. 统一社会信用代码
3. 法定代表人
4. 注册资本
5. 成立日期
6. 经营范围
7. 注册地址
8. 企业类型
9. 经营状态

请以JSON格式返回结果。""",
            task_type="due_diligence",
            context={"company_name": company_name, "task": "basic_info"}
        )
        
        return self._parse_agent_result(result, {
            "name": company_name,
            "legal_representative": "",
            "registered_capital": "",
            "established_date": "",
            "business_scope": "",
            "address": "",
            "company_type": "",
            "status": "正常",
        })
    
    async def _get_litigation_info(self, company_name: str) -> Dict[str, Any]:
        """获取诉讼信息"""
        result = await self.workforce.process_task(
            task_description=f"""请查询企业"{company_name}"的诉讼和法律纠纷信息，包括：
1. 作为原告的案件数量和类型
2. 作为被告的案件数量和类型
3. 重大诉讼案件摘要
4. 执行案件信息
5. 失信被执行人记录

请以JSON格式返回，包含 plaintiff_cases, defendant_cases, major_cases, execution_cases, dishonest_records 字段。""",
            task_type="due_diligence",
            context={"company_name": company_name, "task": "litigation"}
        )
        
        return self._parse_agent_result(result, {
            "plaintiff_cases": 0,
            "defendant_cases": 0,
            "major_cases": [],
            "execution_cases": 0,
            "dishonest_records": 0,
            "risk_level": "low",
        })
    
    async def _get_credit_info(self, company_name: str) -> Dict[str, Any]:
        """获取信用信息"""
        result = await self.workforce.process_task(
            task_description=f"""请评估企业"{company_name}"的信用状况，包括：
1. 行政处罚记录
2. 税务违规记录
3. 环保处罚记录
4. 经营异常信息
5. 严重违法信息
6. 信用评级建议 (A/B/C/D)

请以JSON格式返回结果。""",
            task_type="due_diligence",
            context={"company_name": company_name, "task": "credit"}
        )
        
        return self._parse_agent_result(result, {
            "administrative_penalties": 0,
            "tax_violations": 0,
            "environmental_penalties": 0,
            "abnormal_operations": 0,
            "serious_violations": 0,
            "credit_rating": "B",
        })
    
    async def _assess_risks(self, company_name: str) -> Dict[str, Any]:
        """风险评估"""
        result = await self.workforce.process_task(
            task_description=f"""请对企业"{company_name}"进行综合法律风险评估：
1. 经营风险 (0-100分)
2. 诉讼风险 (0-100分)
3. 信用风险 (0-100分)
4. 合规风险 (0-100分)
5. 关联风险 (0-100分)
6. 总体风险评级 (low/medium/high/critical)
7. 主要风险点描述
8. 风险防范建议

请以JSON格式返回，包含各项评分和建议。""",
            task_type="risk_assessment",
            context={"company_name": company_name}
        )
        
        return self._parse_agent_result(result, {
            "operation_risk": 30,
            "litigation_risk": 20,
            "credit_risk": 25,
            "compliance_risk": 20,
            "relation_risk": 15,
            "overall_rating": "low",
            "risk_points": [],
            "recommendations": [],
        })
    
    async def _get_company_relations(self, company_name: str) -> Dict[str, Any]:
        """获取企业关联关系"""
        result = await self.workforce.process_task(
            task_description=f"""请分析企业"{company_name}"的关联关系：
1. 股东信息（名称、持股比例、类型）
2. 对外投资（被投资企业、持股比例）
3. 分支机构
4. 主要人员（高管、董事）
5. 实际控制人

请以JSON格式返回，用于构建企业关系图谱。""",
            task_type="due_diligence",
            context={"company_name": company_name, "task": "relations"}
        )
        
        return self._parse_agent_result(result, {
            "shareholders": [],
            "investments": [],
            "branches": [],
            "key_persons": [],
            "actual_controller": None,
        })
    
    async def _generate_report(
        self,
        company_name: str,
        results: Dict[str, Any],
        investigation_type: str,
    ) -> Dict[str, Any]:
        """生成调查报告"""
        # 汇总信息生成报告
        summary_prompt = f"""
基于以下调查结果，为企业"{company_name}"生成尽职调查报告摘要：

调查类型: {investigation_type}
调查结果: {results}

请生成：
1. 企业概况（100字以内）
2. 主要发现（3-5条要点）
3. 风险提示（如有）
4. 建议措施
5. 总体评价

以JSON格式返回。
"""
        
        result = await self.workforce.process_task(
            task_description=summary_prompt,
            task_type="due_diligence",
        )
        
        return self._parse_agent_result(result, {
            "overview": f"关于{company_name}的尽职调查报告",
            "findings": [],
            "risk_alerts": [],
            "recommendations": [],
            "conclusion": "",
        })
    
    def _parse_agent_result(
        self,
        result: Dict,
        default: Dict[str, Any],
    ) -> Dict[str, Any]:
        """解析智能体返回结果"""
        import json
        import re
        
        try:
            final_result = result.get("final_result", {})
            
            if isinstance(final_result, dict):
                return {**default, **final_result}
            
            if isinstance(final_result, str):
                # 尝试提取 JSON
                json_match = re.search(r'\{[\s\S]*\}', final_result)
                if json_match:
                    parsed = json.loads(json_match.group())
                    return {**default, **parsed}
            
            return default
            
        except Exception as e:
            logger.warning(f"解析结果失败: {e}")
            return default
    
    def build_company_graph(
        self,
        company_name: str,
        relations: Dict[str, Any],
    ) -> Dict[str, Any]:
        """构建企业关系图谱"""
        nodes = []
        edges = []
        
        # 中心节点（目标企业）
        nodes.append({
            "id": "center",
            "name": company_name,
            "type": "target",
            "level": 0,
        })
        
        # 股东节点
        for i, shareholder in enumerate(relations.get("shareholders", [])):
            node_id = f"shareholder_{i}"
            nodes.append({
                "id": node_id,
                "name": shareholder.get("name", f"股东{i+1}"),
                "type": "shareholder",
                "level": 1,
            })
            edges.append({
                "source": node_id,
                "target": "center",
                "relation": "股东",
                "label": shareholder.get("ratio", ""),
            })
        
        # 投资节点
        for i, investment in enumerate(relations.get("investments", [])):
            node_id = f"investment_{i}"
            nodes.append({
                "id": node_id,
                "name": investment.get("name", f"被投资企业{i+1}"),
                "type": "investment",
                "level": 1,
            })
            edges.append({
                "source": "center",
                "target": node_id,
                "relation": "投资",
                "label": investment.get("ratio", ""),
            })
        
        # 关键人员节点
        for i, person in enumerate(relations.get("key_persons", [])):
            node_id = f"person_{i}"
            nodes.append({
                "id": node_id,
                "name": person.get("name", f"高管{i+1}"),
                "type": "person",
                "level": 1,
            })
            edges.append({
                "source": node_id,
                "target": "center",
                "relation": person.get("position", "高管"),
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "center": company_name,
        }


# 模拟企业数据（用于演示）
MOCK_COMPANY_DATA = {
    "阿里巴巴": {
        "basic_info": {
            "name": "阿里巴巴集团控股有限公司",
            "legal_representative": "蔡崇信",
            "registered_capital": "约7500亿美元市值",
            "established_date": "1999-09-09",
            "business_scope": "电子商务、云计算、数字媒体、创新业务",
            "address": "中国杭州",
            "company_type": "外商投资企业",
            "status": "正常",
        },
        "risk": {
            "operation_risk": 25,
            "litigation_risk": 35,
            "credit_risk": 20,
            "compliance_risk": 30,
            "relation_risk": 25,
            "overall_rating": "medium",
            "risk_points": ["反垄断合规风险", "跨境监管风险"],
        }
    },
    "腾讯": {
        "basic_info": {
            "name": "腾讯控股有限公司",
            "legal_representative": "马化腾",
            "registered_capital": "约4万亿港元市值",
            "established_date": "1998-11-11",
            "business_scope": "社交网络、数字内容、金融科技、企业服务",
            "address": "中国深圳",
            "company_type": "外商投资企业",
            "status": "正常",
        },
        "risk": {
            "operation_risk": 20,
            "litigation_risk": 30,
            "credit_risk": 15,
            "compliance_risk": 35,
            "relation_risk": 20,
            "overall_rating": "low",
        }
    }
}


def _deterministic_hash(s: str, mod: int = 100) -> int:
    """基于字符串生成确定性的数值（同一输入总是返回相同结果）"""
    import hashlib
    h = int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16)
    return h % mod


def _generate_deterministic_company_data(company_name: str) -> Dict[str, Any]:
    """
    基于公司名称确定性生成企业数据（非随机）。
    同一公司名多次查询结果完全一致。
    用于 AI Agent 不可用时的回退方案。
    """
    h = _deterministic_hash

    # 确定性的法定代表人（基于公司名）
    surnames = ["李", "王", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴"]
    given = ["明", "华", "强", "伟", "芳", "敏", "静", "磊", "洋", "军"]
    legal_rep = surnames[h(company_name + "surname", 10)] + given[h(company_name + "given", 10)]

    # 确定性注册资本
    capital_base = h(company_name + "capital", 50) * 100 + 100  # 100 ~ 5100
    capital = f"{capital_base}万元"

    # 确定性成立年份
    year = 2000 + h(company_name + "year", 24)
    month = 1 + h(company_name + "month", 12)
    day = 1 + h(company_name + "day", 28)
    established = f"{year}-{month:02d}-{day:02d}"

    # 行业推断
    industry_map = {
        "科技": "技术开发、技术咨询、技术服务、软件开发",
        "贸易": "货物进出口、技术进出口、国内贸易",
        "建筑": "建筑工程施工、装饰装修工程、市政公用工程",
        "食品": "食品生产、食品销售、餐饮服务",
        "医药": "药品研发、医疗器械销售、医药技术咨询",
        "教育": "教育咨询、教育培训、文化交流",
        "金融": "投资咨询、资产管理、财务顾问",
        "物流": "国内货运代理、仓储服务、供应链管理",
    }
    scope = "技术服务、软件开发、信息咨询"
    for keyword, biz in industry_map.items():
        if keyword in company_name:
            scope = biz
            break

    # 城市推断
    city_map = {
        "北京": "北京市海淀区", "上海": "上海市浦东新区",
        "广州": "广州市天河区", "深圳": "深圳市南山区",
        "杭州": "杭州市余杭区", "成都": "成都市高新区",
        "武汉": "武汉市东湖高新区", "南京": "南京市雨花台区",
    }
    address = "北京市朝阳区"
    for city, addr in city_map.items():
        if city in company_name:
            address = addr
            break

    # 公司类型推断
    company_type = "有限责任公司"
    if "集团" in company_name:
        company_type = "有限责任公司(自然人投资或控股)"
    elif "股份" in company_name:
        company_type = "股份有限公司"

    # 确定性诉讼数据
    plaintiff = h(company_name + "plaintiff", 8)
    defendant = h(company_name + "defendant", 12)
    execution = h(company_name + "execution", 4)

    # 确定性风险评分
    op_risk = 15 + h(company_name + "op_risk", 40)
    lit_risk = 10 + h(company_name + "lit_risk", 50)
    cred_risk = 10 + h(company_name + "cred_risk", 35)
    comp_risk = 10 + h(company_name + "comp_risk", 40)
    rel_risk = 5 + h(company_name + "rel_risk", 35)
    avg_risk = (op_risk + lit_risk + cred_risk + comp_risk + rel_risk) / 5
    overall = "low" if avg_risk < 30 else ("medium" if avg_risk < 50 else "high")

    # 风险点
    risk_points = []
    if lit_risk > 40:
        risk_points.append("诉讼案件较多，存在法律纠纷风险")
    if cred_risk > 35:
        risk_points.append("信用评级偏低，需关注偿债能力")
    if comp_risk > 35:
        risk_points.append("合规管理需加强，存在监管处罚风险")
    if defendant > 5:
        risk_points.append(f"作为被告案件 {defendant} 起，需重点关注")

    return {
        "basic_info": {
            "name": company_name,
            "legal_representative": legal_rep,
            "registered_capital": capital,
            "established_date": established,
            "business_scope": scope,
            "address": address,
            "company_type": company_type,
            "status": "正常",
        },
        "litigation": {
            "plaintiff_cases": plaintiff,
            "defendant_cases": defendant,
            "execution_cases": execution,
            "dishonest_records": h(company_name + "dishonest", 3),
            "major_cases": [],
            "risk_level": "low" if defendant < 3 else ("medium" if defendant < 7 else "high"),
        },
        "credit": {
            "credit_rating": ["A", "A", "B", "B", "B", "C"][h(company_name + "credit_r", 6)],
            "administrative_penalties": h(company_name + "admin_pen", 5),
            "tax_violations": h(company_name + "tax_vio", 3),
            "environmental_penalties": h(company_name + "env_pen", 3),
            "abnormal_operations": h(company_name + "abnormal", 2),
            "serious_violations": 0,
        },
        "risk": {
            "operation_risk": op_risk,
            "litigation_risk": lit_risk,
            "credit_risk": cred_risk,
            "compliance_risk": comp_risk,
            "relation_risk": rel_risk,
            "overall_rating": overall,
            "risk_points": risk_points,
            "recommendations": [
                "建议定期跟踪企业诉讼动态",
                "建议核查企业最新年报财务数据",
                "建议了解实际控制人关联企业情况",
            ],
        },
    }


async def get_company_info(company_name: str, max_retries: int = 3) -> Dict[str, Any]:
    """
    获取企业信息。
    优先使用快速模式（单次 LLM 调用），失败后重试。
    """
    # 1. 预置知名企业数据
    # 仅开发模式下使用预置示例数据
    if settings.DEV_MODE and company_name in MOCK_COMPANY_DATA:
        return MOCK_COMPANY_DATA[company_name]

    # 2. 快速模式（单次 LLM 调用，带重试）
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"快速尽调第 {attempt}/{max_retries} 次尝试: {company_name}")
            result = await asyncio.wait_for(
                due_diligence_service.quick_investigate(company_name),
                timeout=60.0,
            )
            if result and result.get("basic_info"):
                if attempt > 1:
                    logger.info(f"快速尽调第 {attempt} 次重试成功: {company_name}")
                return result
            last_error = Exception("LLM 返回结果为空")
        except asyncio.TimeoutError:
            last_error = Exception("AI 调查超时（60秒）")
            logger.warning(f"快速尽调超时，第 {attempt}/{max_retries} 次尝试: {company_name}")
        except Exception as e:
            last_error = e
            logger.warning(f"快速尽调异常，第 {attempt}/{max_retries} 次尝试: {company_name} - {e}")

        # 非最后一次，等待后重试
        if attempt < max_retries:
            wait_seconds = attempt * 2  # 递增等待: 2s, 4s
            logger.info(f"等待 {wait_seconds}s 后重试...")
            await asyncio.sleep(wait_seconds)

    # 3 次全部失败
    raise Exception(f"AI 调查失败（已重试 {max_retries} 次），请检查 LLM 服务是否可用（企业: {company_name}）")


# 保留旧名称的兼容别名
async def get_mock_company_info(company_name: str) -> Dict[str, Any]:
    """向后兼容的别名 — 内部改为确定性数据"""
    # 仅开发模式下使用预置示例数据
    if settings.DEV_MODE and company_name in MOCK_COMPANY_DATA:
        return MOCK_COMPANY_DATA[company_name]
    return _generate_deterministic_company_data(company_name)


# 创建全局实例
due_diligence_service = DueDiligenceService()
