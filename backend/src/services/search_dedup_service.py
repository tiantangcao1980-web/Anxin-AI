# -*- coding: utf-8 -*-
"""
搜索结果去重与质量评分

功能：
1. URL 去重 — 相同 URL 只保留最高分
2. 内容相似度去重 — 标题/摘要相似度 > 0.8 合并
3. 来源可信度评分 — 政府网站 > 专业法律站 > 新闻 > 社交媒体
4. 多源结果 RRF 合并排序
"""

import re
from typing import List, Dict, Any
from urllib.parse import urlparse
from loguru import logger


# 域名可信度分级
DOMAIN_TRUST_SCORES: Dict[str, float] = {
    # 政府官方（最可信）
    "gov.cn": 1.0,
    "court.gov.cn": 1.0,
    "creditchina.gov.cn": 1.0,
    "gsxt.gov.cn": 1.0,
    "moj.gov.cn": 0.95,
    "npc.gov.cn": 0.95,

    # 法律专业平台
    "pkulaw.com": 0.9,
    "itslaw.com": 0.85,
    "lawxp.com": 0.85,
    "chinalawinfo.com": 0.85,
    "wenshu.court.gov.cn": 0.95,

    # 企业信息平台
    "tianyancha.com": 0.8,
    "qcc.com": 0.8,
    "aiqicha.baidu.com": 0.75,
    "qichacha.com": 0.75,

    # 主流媒体
    "xinhuanet.com": 0.7,
    "people.com.cn": 0.7,
    "caixin.com": 0.65,
    "thepaper.cn": 0.65,

    # 百科/知识
    "baike.baidu.com": 0.6,
    "zh.wikipedia.org": 0.6,

    # 社交媒体（最低）
    "weibo.com": 0.3,
    "zhihu.com": 0.4,
    "douyin.com": 0.2,
}

# 默认可信度（未知域名）
DEFAULT_TRUST = 0.5


class SearchDedupService:
    """搜索结果去重与质量评分"""

    def deduplicate(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        URL 去重 + 内容相似度去重

        保留策略：相同 URL 或内容极度相似时保留 relevance 最高的
        """
        if not results:
            return []

        seen_urls = {}  # url → result index
        seen_titles = {}  # normalized_title → result index
        deduped = []

        for r in results:
            url = r.get("url", "")
            title = r.get("title", "")

            # URL 去重
            normalized_url = self._normalize_url(url)
            if normalized_url in seen_urls:
                existing_idx = seen_urls[normalized_url]
                if r.get("relevance", 0) > deduped[existing_idx].get("relevance", 0):
                    deduped[existing_idx] = r
                continue

            # 标题相似度去重
            norm_title = self._normalize_title(title)
            if norm_title and norm_title in seen_titles:
                existing_idx = seen_titles[norm_title]
                if r.get("relevance", 0) > deduped[existing_idx].get("relevance", 0):
                    deduped[existing_idx] = r
                continue

            idx = len(deduped)
            deduped.append(r)
            if normalized_url:
                seen_urls[normalized_url] = idx
            if norm_title:
                seen_titles[norm_title] = idx

        return deduped

    def score_quality(self, result: Dict[str, Any]) -> float:
        """
        来源可信度评分

        Returns:
            0.0 - 1.0 的可信度分数
        """
        url = result.get("url", "")
        if not url:
            return DEFAULT_TRUST

        domain = self._extract_domain(url)

        # 精确匹配
        for pattern, score in DOMAIN_TRUST_SCORES.items():
            if pattern in domain:
                return score

        return DEFAULT_TRUST

    def merge_multi_source(
        self,
        *result_lists: List[Dict[str, Any]],
        k: int = 60,
    ) -> List[Dict[str, Any]]:
        """
        多源结果 RRF 合并排序

        Reciprocal Rank Fusion: 综合多个引擎的排名
        最终排序 = RRF_score + quality_score * 0.3
        """
        score_map: Dict[str, float] = {}
        item_map: Dict[str, Dict] = {}

        for list_idx, results in enumerate(result_lists):
            weight = 1.0 / (list_idx + 1)  # 前面的列表权重更高
            for rank, result in enumerate(results):
                key = self._result_key(result)
                rrf = weight / (k + rank + 1)
                quality = self.score_quality(result) * 0.3

                score_map[key] = score_map.get(key, 0) + rrf + quality

                if key not in item_map or result.get("relevance", 0) > item_map[key].get("relevance", 0):
                    item_map[key] = result

        # 排序
        sorted_keys = sorted(score_map, key=score_map.get, reverse=True)

        merged = []
        for key in sorted_keys:
            item = item_map[key]
            item["merged_score"] = round(score_map[key], 4)
            item["trust_score"] = round(self.score_quality(item), 2)
            merged.append(item)

        # 去重
        return self.deduplicate(merged)

    # ===== 工具方法 =====

    def _normalize_url(self, url: str) -> str:
        """URL 标准化（去掉 www、尾部斜杠、query 参数中的追踪参数）"""
        if not url:
            return ""
        url = url.strip().rstrip("/")
        url = re.sub(r'^https?://(www\.)?', '', url)
        url = re.sub(r'[?&](utm_\w+|ref|source|from)=[^&]*', '', url)
        return url.lower()

    def _normalize_title(self, title: str) -> str:
        """标题标准化（去掉标点、空格、截断到前 30 字）"""
        if not title:
            return ""
        t = re.sub(r'[\s\-_—|·•·]+', '', title)
        t = re.sub(r'[^\u4e00-\u9fff\w]', '', t)
        return t[:30].lower()

    def _extract_domain(self, url: str) -> str:
        """提取域名"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower().replace("www.", "")
        except Exception:
            return ""

    def _result_key(self, result: Dict) -> str:
        """生成结果唯一键"""
        url = self._normalize_url(result.get("url", ""))
        if url:
            return url
        return self._normalize_title(result.get("title", "")) or str(id(result))


# 全局实例
search_dedup_service = SearchDedupService()
