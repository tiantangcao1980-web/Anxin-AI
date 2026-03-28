# -*- coding: utf-8 -*-
"""
数据清洗服务
使用 LLM 从原始 HTML 中提取法律实体
兼容 OpenAI 兼容 API 和本地模型服务（如 LM Studio）
"""

import json
from typing import Dict, Any
from loguru import logger
import httpx

from src.core.llm_helper import get_llm_config_sync


SYSTEM_PROMPT = (
    "你是一个法务数据专家。你的任务是从原始 HTML 或文本中提取法律案件关键信息。"
    "请严格按 JSON 格式输出，不要包含任何 Markdown 格式。包含以下字段：\n"
    "- court_name: 法院名称\n"
    "- parties: 当事人（原告、被告等，以列表形式）\n"
    "- amount: 标的额（数值或描述，如 100万元）\n"
    "- legal_provisions: 法律关系条文（提取提到的法律法规，以列表形式）\n"
    "如果某个字段无法提取，请填入 null。"
)


class DataCleaner:
    """法务情报数据清洗管道"""

    def __init__(self):
        self._llm_config = None
        self._is_local_api = False
        self._url = ""
        self._headers: Dict[str, str] = {}
        self._model_name = ""
        self._init()

    def _init(self):
        """初始化 LLM 配置"""
        try:
            cfg = get_llm_config_sync("llm")
            self._llm_config = cfg
            self._model_name = cfg.model_name

            api_key = cfg.api_key or ""
            base_url = (cfg.api_base_url or "").rstrip("/")

            self._headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            # 判断是否为本地模型服务（URL 含 /api/v1/chat）
            if "/api/v1/chat" in base_url:
                self._is_local_api = True
                self._url = base_url  # 直接使用，不拼接
            elif base_url.endswith("/chat/completions"):
                self._url = base_url
            else:
                self._url = f"{base_url}/chat/completions"

            logger.info(
                f"DataCleaner 初始化成功 "
                f"(model={self._model_name}, local={self._is_local_api}, url={self._url})"
            )
        except Exception as e:
            logger.error(f"DataCleaner 初始化失败: {e}")

    @staticmethod
    def _parse_json_tolerant(text: str) -> Any:
        """容错解析 JSON（处理 LLM 常见的格式问题）"""
        import re

        # 1. 标准解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. 去除 ```json ... ``` 包裹
        cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 3. 单引号 → 双引号
        try:
            return json.loads(cleaned.replace("'", '"'))
        except json.JSONDecodeError:
            pass

        # 4. 移除行尾注释 // ... 和尾部逗号
        no_comments = re.sub(r"//[^\n]*", "", cleaned)
        no_trailing = re.sub(r",\s*([}\]])", r"\1", no_comments)
        try:
            return json.loads(no_trailing)
        except json.JSONDecodeError:
            pass

        logger.warning(f"JSON 容错解析仍失败: {text[:150]}")
        return None

    async def clean_html(self, html_content: str) -> Dict[str, Any]:
        """从 HTML 中提取法务实体"""
        if not self._url:
            logger.error("DataCleaner 未初始化，无法调用 LLM")
            return {}

        logger.info("开始清洗法务数据...")

        # 兼容传入 list 的情况（如多段 HTML）
        if isinstance(html_content, list):
            html_content = "\n".join(str(item) for item in html_content)

        # 限制长度
        text_content = str(html_content)[:8000]
        user_content = f"请分析以下内容并提取信息：\n\n{text_content}"

        # 构造请求体
        if self._is_local_api:
            input_text = f"[系统指令] {SYSTEM_PROMPT}\n\n{user_content}"
            payload = {
                "model": self._model_name,
                "input": input_text,
                "stream": False,
            }
        else:
            payload = {
                "model": self._model_name,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0,
                "max_tokens": 4096,
            }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(self._url, headers=self._headers, json=payload)

            if resp.status_code != 200:
                logger.error(f"LLM 返回 {resp.status_code}: {resp.text[:200]}")
                return {}

            data = resp.json()

            # 提取回复内容（兼容 OpenAI 格式和自定义格式）
            content = ""
            if "choices" in data and data["choices"]:
                msg = data["choices"][0].get("message", {})
                raw = msg.get("content", "")
                # 兼容 content 为数组的情况，如 [{"type":"text","text":"..."}]
                if isinstance(raw, list):
                    content = "".join(
                        item.get("text", str(item)) if isinstance(item, dict) else str(item)
                        for item in raw
                    )
                else:
                    content = str(raw) if raw else ""
            elif "response" in data:
                content = str(data["response"])
            elif "output" in data:
                # 本地模型返回格式: {"output": [{"type": "message", "content": "..."}]}
                output = data["output"]
                if isinstance(output, list):
                    content = "".join(
                        item.get("content", "") if isinstance(item, dict) else str(item)
                        for item in output
                    )
                else:
                    content = str(output)

            if not content:
                logger.warning("LLM 返回内容为空")
                return {}

            # 提取 JSON
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                result = self._parse_json_tolerant(json_str)
                if result is not None:
                    non_null = [k for k, v in result.items() if v is not None]
                    logger.info(
                        f"数据清洗完成: 提取到 {len(non_null)}/{len(result)} 个字段 "
                        f"{non_null or '(无有效数据)'}"
                    )
                    return result

            logger.warning(f"未能从 LLM 响应中解析出 JSON: {content[:200]}")
            return {}

        except Exception as e:
            logger.error(f"数据清洗过程中发生错误: {e}")
            return {}


# 全局单例
data_cleaner = DataCleaner()
