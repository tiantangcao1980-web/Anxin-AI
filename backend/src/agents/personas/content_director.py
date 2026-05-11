# -*- coding: utf-8 -*-
"""ContentDirectorAgent —— V3 P7-D「内容总监」 persona。

定位：制造业品牌内容自动化（公众号 / 短视频脚本 / 海报 / banner / 包装）。

为什么不是单 capability 工具？
    内容生产是"角色级"任务：同一句"做一篇产品上市公众号"会涉及
        - 选题 / 标题 (LLM)
        - 正文写作 + SEO (LLM)
        - 配图建议 (调 docx / canvas-design skill)
        - 品牌一致性校验（违禁词 + tone）
        - 多语言本地化（出海跨境）
    所以单独成一个 persona，对外暴露 5 个 capability。

调度的 skills：docx (文章导出)、pptx (banner 出图)、canvas-design / brand-guidelines /
theme-factory (视觉)。
OAuth 集成：微信公众号（仅授权后才能发布）、Figma、Canva、TikTok 平台。
"""

from __future__ import annotations

import json
import re
from typing import Any

from src.agents.personas.base_persona import BasePersonaAgent
from src.agents.personas.content_models import (
    ArticleDraft,
    BrandProfile,
    ConsistencyReport,
    PosterCopy,
    VideoScene,
    VideoScript,
)


# ---------------------------------------------------------------------------
# Prompt 常量（独立出来便于测试 patch）
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """你是「内容总监」，专为中国制造业 / 跨境品牌做内容自动化。

你的职责：
1. 公众号长文（含 SEO 标题 × 3、200 字摘要、≥1500 字正文、配图建议）
2. 短视频脚本（分镜 + 字幕 + 时长 + BGM 推荐，按平台区分 TikTok/抖音/视频号/Shorts）
3. 海报 / banner / 包装文案（多尺寸、多版本，每版本含 headline / sub / body / CTA）
4. 品牌一致性检查（理念色 / 字体 / tone / 用词规范 / 违禁词）
5. 多语言本地化（不只翻译，还要做市场语境改写）

风格守则：
- 文案要"具体"不要"漂亮话"：能写"误差 ≤ 5μm"就别写"匠心精度"。
- 每篇内容必须紧扣 BrandProfile（tone / voice / forbidden_words），违禁词触发 block。
- 输出严格按调用方要求的 JSON schema，不解释、不寒暄。
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class ContentDirectorAgent(BasePersonaAgent):
    """内容总监 persona。"""

    persona_id = "content_director"
    display_name = "内容总监"
    emoji = "✍️"
    description = "公众号 / 短视频 / 海报 / 品牌一致性 / 多语言本地化的内容自动化"
    backed_by_skills = ["docx", "pptx"]
    supported_apps = ["wechat_mp", "figma", "canva", "tiktok_shop"]
    capabilities = [
        "wechat_article_drafting",
        "video_script_generation",
        "poster_copy_generation",
        "brand_consistency_check",
        "i18n_localization",
    ]

    SYSTEM_PROMPT = _SYSTEM_PROMPT

    # 平台默认时长上限（秒），限制 LLM 别天马行空
    _PLATFORM_MAX_SEC = {
        "tiktok": 60,
        "douyin": 60,
        "youtube_shorts": 60,
        "video_account": 90,
        "xiaohongshu": 60,
    }

    # ------------------------------------------------------------------
    # capability 1: 公众号长文
    # ------------------------------------------------------------------

    async def draft_wechat_article(
        self,
        topic: str,
        brand: BrandProfile,
        length: int = 1500,
    ) -> ArticleDraft:
        """生成公众号长文草稿。

        - length：目标字数（最少 800，最多 5000，默认 1500）
        - 输出 ArticleDraft（含 3 个 SEO 标题 + 摘要 + body_markdown + 配图建议）
        - 内部会做 forbidden_words 兜底过滤
        """

        length = max(800, min(int(length), 5000))
        prompt = self._build_article_prompt(topic, brand, length)
        raw = await self._llm(prompt, system=self.SYSTEM_PROMPT)
        parsed = self._safe_json_loads(raw, fallback=self._article_fallback(topic, brand))

        title_options = self._coerce_str_list(parsed.get("title_options"), max_items=5)[:3]
        if len(title_options) < 3:
            # 兜底补足，避免上游空数组
            title_options += [topic] * (3 - len(title_options))

        body = str(parsed.get("body_markdown") or "")
        body = self._scrub_forbidden(body, brand.forbidden_words)

        return ArticleDraft(
            title_options=title_options,
            summary=str(parsed.get("summary") or "")[:300],
            body_markdown=body,
            suggested_cover=str(parsed.get("suggested_cover") or ""),
            suggested_inline_images=self._coerce_str_list(parsed.get("suggested_inline_images")),
            estimated_read_time_min=max(1, len(body) // 400),
            seo_keywords=self._coerce_str_list(parsed.get("seo_keywords"), max_items=10),
            hashtags=self._coerce_str_list(parsed.get("hashtags"), max_items=8),
        )

    # ------------------------------------------------------------------
    # capability 2: 短视频脚本
    # ------------------------------------------------------------------

    async def generate_video_script(
        self,
        topic: str,
        platform: str,
        duration_sec: int,
    ) -> VideoScript:
        """按平台 + 时长生成分镜脚本。

        - platform 必须在 _PLATFORM_MAX_SEC 范围内
        - duration_sec 会被钳到平台上限
        """

        platform_norm = (platform or "").strip().lower()
        if platform_norm not in self._PLATFORM_MAX_SEC:
            raise ValueError(f"不支持的视频平台: {platform!r}（支持: {list(self._PLATFORM_MAX_SEC)})")
        max_sec = self._PLATFORM_MAX_SEC[platform_norm]
        duration_sec = max(5, min(int(duration_sec), max_sec))

        prompt = self._build_video_prompt(topic, platform_norm, duration_sec)
        raw = await self._llm(prompt, system=self.SYSTEM_PROMPT)
        parsed = self._safe_json_loads(raw, fallback={})

        scenes_raw = parsed.get("scenes") or []
        scenes: list[VideoScene] = []
        for idx, item in enumerate(scenes_raw, start=1):
            if not isinstance(item, dict):
                continue
            scenes.append(
                VideoScene(
                    scene_no=int(item.get("scene_no") or idx),
                    duration_sec=max(1, int(item.get("duration_sec") or 3)),
                    visual=str(item.get("visual") or ""),
                    voiceover=str(item.get("voiceover") or ""),
                    on_screen_text=str(item.get("on_screen_text") or ""),
                    bgm_mood=str(item.get("bgm_mood") or ""),
                )
            )
        if not scenes:
            scenes = [
                VideoScene(scene_no=1, duration_sec=duration_sec, visual=topic, voiceover=topic)
            ]

        return VideoScript(
            platform=platform_norm,
            total_duration_sec=sum(s.duration_sec for s in scenes) or duration_sec,
            scenes=scenes,
            hook=str(parsed.get("hook") or "")[:200],
            cta=str(parsed.get("cta") or "")[:200],
            hashtags=self._coerce_str_list(parsed.get("hashtags"), max_items=10),
            bgm_suggestions=self._coerce_str_list(parsed.get("bgm_suggestions"), max_items=5),
        )

    # ------------------------------------------------------------------
    # capability 3: 海报 / banner 文案
    # ------------------------------------------------------------------

    async def generate_poster_copy(
        self,
        occasion: str,
        sizes: list[str],
        brand: BrandProfile,
    ) -> list[PosterCopy]:
        """对一组尺寸生成对应的海报文案。

        sizes 形如 ["1080x1080", "1080x1920", "1920x1080"]。
        每个尺寸单独 LLM 调用，避免长尾尺寸串扰；
        失败的尺寸用 fallback 兜底，不抛异常（前端能拿到完整列表）。
        """

        sizes = [s.strip() for s in (sizes or []) if s and self._valid_size(s)]
        if not sizes:
            raise ValueError("sizes 至少要给一个，例如 '1080x1080'")

        results: list[PosterCopy] = []
        for size in sizes:
            try:
                prompt = self._build_poster_prompt(occasion, size, brand)
                raw = await self._llm(prompt, system=self.SYSTEM_PROMPT)
                parsed = self._safe_json_loads(raw, fallback={})
                copy = PosterCopy(
                    size=size,
                    headline=self._scrub_forbidden(str(parsed.get("headline") or occasion), brand.forbidden_words),
                    sub_headline=self._scrub_forbidden(str(parsed.get("sub_headline") or ""), brand.forbidden_words),
                    body=self._scrub_forbidden(str(parsed.get("body") or ""), brand.forbidden_words),
                    cta=str(parsed.get("cta") or "立即了解"),
                    visual_description=str(parsed.get("visual_description") or ""),
                    layout_hint=str(parsed.get("layout_hint") or ""),
                )
            except Exception:  # noqa: BLE001 — 单个尺寸失败不应拖垮整组
                copy = PosterCopy(
                    size=size,
                    headline=occasion,
                    sub_headline="",
                    body="",
                    cta="立即了解",
                    visual_description=f"主色 {brand.primary_color}",
                    layout_hint="fallback",
                )
            results.append(copy)
        return results

    # ------------------------------------------------------------------
    # capability 4: 品牌一致性检查
    # ------------------------------------------------------------------

    async def check_brand_consistency(
        self,
        content: str,
        brand: BrandProfile,
    ) -> ConsistencyReport:
        """两层检测：

        1) 确定性规则层（本地、瞬时）：
           - forbidden_words 命中 → severity=block
           - voice 关键词覆盖率 < 30% → severity=warn
           - 长度异常 → severity=info
        2) LLM 评分层（非确定性、慢）：tone 是否对得上、是否有 AI 套话。
           为了"既精准又快"：用规则层先打地基，再用一次小 prompt 让 LLM 只输出
           {"tone_score": 0~1, "ai_taste_score": 0~1, "extra_issues":[]}，
           避免让 LLM 重复做规则就能解的事。
        """

        content = content or ""
        issues: list[dict[str, Any]] = []
        suggestions: list[str] = []

        # ---------- 规则层 ----------
        for word in brand.forbidden_words or []:
            if word and word in content:
                issues.append(
                    {
                        "field": "forbidden_words",
                        "expected": f"不出现「{word}」",
                        "actual": f"命中「{word}」",
                        "severity": "block",
                    }
                )
                suggestions.append(f"删除或替换违禁词「{word}」后再发布")

        voice_hits = sum(1 for w in (brand.voice or []) if w and w in content)
        voice_total = max(1, len(brand.voice or []))
        voice_coverage = voice_hits / voice_total
        if brand.voice and voice_coverage < 0.3:
            issues.append(
                {
                    "field": "voice",
                    "expected": f"覆盖品牌关键词 ≥ 30%（共 {voice_total} 个）",
                    "actual": f"仅 {voice_hits}/{voice_total} = {voice_coverage:.0%}",
                    "severity": "warn",
                }
            )
            suggestions.append("适度植入品牌语汇，例如：" + "、".join(brand.voice[:3]))

        if len(content) < 80:
            issues.append(
                {"field": "length", "expected": "正文 ≥ 80 字", "actual": f"{len(content)} 字", "severity": "info"}
            )

        # ---------- LLM 层（精简评分） ----------
        rule_score = 1.0
        if any(it["severity"] == "block" for it in issues):
            rule_score = 0.0
        elif any(it["severity"] == "warn" for it in issues):
            rule_score = 0.6
        elif any(it["severity"] == "info" for it in issues):
            rule_score = 0.85

        try:
            llm_prompt = self._build_consistency_prompt(content, brand)
            raw = await self._llm(llm_prompt, system=self.SYSTEM_PROMPT)
            llm_parsed = self._safe_json_loads(raw, fallback={"tone_score": 0.7, "ai_taste_score": 0.7})
            tone_score = float(llm_parsed.get("tone_score") or 0.7)
            ai_taste_score = float(llm_parsed.get("ai_taste_score") or 0.7)
            for extra in llm_parsed.get("extra_issues") or []:
                if isinstance(extra, dict):
                    extra.setdefault("severity", "info")
                    issues.append(extra)
        except Exception:  # noqa: BLE001 — LLM 不可达时退化为纯规则
            tone_score = 0.7
            ai_taste_score = 0.7

        # 综合分：规则层是地板，LLM 层做加权
        overall = round(min(rule_score, 0.4 * tone_score + 0.3 * ai_taste_score + 0.3 * rule_score), 3)

        return ConsistencyReport(
            overall_score=overall,
            issues=issues,
            suggestions=suggestions,
        )

    # ------------------------------------------------------------------
    # capability 5: 多语言本地化
    # ------------------------------------------------------------------

    async def localize(
        self,
        content: str,
        target_languages: list[str],
        market_context: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """多语言本地化（含市场语境改写，不只是翻译）。

        market_context 例子：{"region": "US", "audience": "B2B engineers", "tone_shift": "更直接"}。
        返回 {language_code: localized_text}。
        """

        target_languages = [lang.strip() for lang in (target_languages or []) if lang and lang.strip()]
        if not target_languages:
            raise ValueError("target_languages 至少要给一个，例如 'en' / 'ja'")
        ctx = market_context or {}

        out: dict[str, str] = {}
        for lang in target_languages:
            try:
                prompt = self._build_localize_prompt(content, lang, ctx)
                raw = await self._llm(prompt, system=self.SYSTEM_PROMPT)
                # 本地化输出可能不是 JSON，允许纯文本
                text = raw.strip() if isinstance(raw, str) else str(raw)
                # 若 LLM 包了 ```json ... ```，剥一层
                m = re.search(r"```(?:json|text)?\s*(.*?)\s*```", text, re.DOTALL)
                if m:
                    text = m.group(1).strip()
                out[lang] = text
            except Exception:  # noqa: BLE001 — 单语言失败不影响其他
                out[lang] = ""  # 上层可以根据空串重试
        return out

    # ==================================================================
    # Prompt builders（独立方法，便于单测）
    # ==================================================================

    def _build_article_prompt(self, topic: str, brand: BrandProfile, length: int) -> str:
        return (
            "请为以下品牌写一篇公众号文章，并以严格 JSON 输出。\n\n"
            f"# 品牌\n{json.dumps(brand.to_dict(), ensure_ascii=False, indent=2)}\n\n"
            f"# 选题\n{topic}\n\n"
            f"# 目标字数\n约 {length} 字（±20%）\n\n"
            "# 输出 JSON Schema\n"
            "{\n"
            '  "title_options": ["3 个 SEO 标题"],\n'
            '  "summary": "100-200 字摘要",\n'
            '  "body_markdown": "正文（markdown 格式）",\n'
            '  "suggested_cover": "封面图描述",\n'
            '  "suggested_inline_images": ["正文配图描述 ×N"],\n'
            '  "seo_keywords": ["关键词"],\n'
            '  "hashtags": ["话题标签"]\n'
            "}\n"
            "只输出 JSON，不要任何解释。"
        )

    def _build_video_prompt(self, topic: str, platform: str, duration_sec: int) -> str:
        return (
            f"为 {platform} 平台生成一个 {duration_sec} 秒短视频脚本，输出 JSON。\n\n"
            f"# 主题\n{topic}\n\n"
            "# JSON Schema\n"
            "{\n"
            '  "hook": "前 3 秒钩子文案",\n'
            '  "scenes": [{"scene_no":1,"duration_sec":3,"visual":"画面","voiceover":"旁白","on_screen_text":"字幕","bgm_mood":"BGM 情绪"}],\n'
            '  "cta": "结尾引导",\n'
            '  "hashtags": ["话题"],\n'
            '  "bgm_suggestions": ["BGM 推荐曲风/曲名"]\n'
            "}\n"
            f"分镜总时长必须 ≈ {duration_sec} 秒。只输出 JSON。"
        )

    def _build_poster_prompt(self, occasion: str, size: str, brand: BrandProfile) -> str:
        return (
            f"为「{occasion}」生成一张 {size} 尺寸的海报文案，输出 JSON。\n\n"
            f"# 品牌\n{json.dumps(brand.to_dict(), ensure_ascii=False)}\n\n"
            "# JSON Schema\n"
            "{\n"
            '  "headline": "主标题（≤ 14 字，强冲击）",\n'
            '  "sub_headline": "副标题（≤ 24 字）",\n'
            '  "body": "正文（≤ 60 字）",\n'
            '  "cta": "行动号召（≤ 8 字）",\n'
            '  "visual_description": "视觉描述（含主色/构图/元素）",\n'
            '  "layout_hint": "排版建议（左/右/居中 等）"\n'
            "}\n"
            "只输出 JSON。"
        )

    def _build_consistency_prompt(self, content: str, brand: BrandProfile) -> str:
        return (
            "请只对以下内容做 tone + AI 味道两个维度的评分，输出严格 JSON：\n"
            f"# 品牌\n{json.dumps(brand.to_dict(), ensure_ascii=False)}\n\n"
            f"# 内容\n{content[:2000]}\n\n"
            "# JSON Schema\n"
            "{\n"
            '  "tone_score": 0.0-1.0,           // 与 brand.tone 的契合度\n'
            '  "ai_taste_score": 0.0-1.0,        // 1.0 = 完全像人写的, 0.0 = 浓重 AI 套话\n'
            '  "extra_issues": [{"field":"...","expected":"...","actual":"...","severity":"info|warn|block"}]\n'
            "}\n"
            "不要重复检查违禁词或字数（系统已做）。只输出 JSON。"
        )

    def _build_localize_prompt(self, content: str, lang: str, ctx: dict[str, Any]) -> str:
        return (
            f"请把下面这段内容本地化为 {lang}（不是直译，要做市场语境改写）：\n\n"
            f"# 市场上下文\n{json.dumps(ctx, ensure_ascii=False)}\n\n"
            f"# 原文\n{content}\n\n"
            f"输出仅本地化后的文本本身，不要任何标签 / JSON / 解释。"
        )

    # ==================================================================
    # 工具方法
    # ==================================================================

    @staticmethod
    def _safe_json_loads(raw: Any, fallback: dict[str, Any]) -> dict[str, Any]:
        """从 LLM 输出里解析 JSON，剥可能的 ```json ... ``` 围栏。"""
        if isinstance(raw, dict):
            return raw
        text = (raw or "").strip() if isinstance(raw, str) else str(raw)
        if not text:
            return dict(fallback)
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
        # 截到首个 { ... 最后一个 }
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            text = text[first : last + 1]
        try:
            return json.loads(text)
        except Exception:  # noqa: BLE001
            return dict(fallback)

    @staticmethod
    def _coerce_str_list(value: Any, max_items: int = 20) -> list[str]:
        if not isinstance(value, list):
            return []
        out = [str(x) for x in value if x is not None and str(x).strip()]
        return out[:max_items]

    @staticmethod
    def _scrub_forbidden(text: str, forbidden: list[str]) -> str:
        """LLM 偶尔会忘违禁词约束 —— 这里再做一次软兜底，把违禁词替换为 ▢▢。"""
        if not text or not forbidden:
            return text
        out = text
        for w in forbidden:
            if not w:
                continue
            out = out.replace(w, "▢▢")
        return out

    @staticmethod
    def _valid_size(size: str) -> bool:
        return bool(re.fullmatch(r"\d{2,5}x\d{2,5}", size or ""))

    @staticmethod
    def _article_fallback(topic: str, brand: BrandProfile) -> dict[str, Any]:
        """LLM 不可达时的最小可用兜底（避免接口直接失败）。"""
        return {
            "title_options": [topic, f"{brand.name}：{topic}", f"重新认识{topic}"],
            "summary": f"{brand.name} 关于「{topic}」的最新观点。",
            "body_markdown": f"# {topic}\n\n（草稿生成失败，请重试）",
            "suggested_cover": f"{brand.primary_color} 主色背景 + 标题文字",
            "suggested_inline_images": [],
            "seo_keywords": [topic, brand.name],
            "hashtags": [],
        }
