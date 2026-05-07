"""
LLM 法律实体关系抽取服务
使用 LLM 从法律文本中提取实体和关系
"""

import json
from typing import Any

from loguru import logger

EXTRACTION_PROMPT = """你是一个专业的法律信息抽取助手。请从以下法律文本中提取实体和关系。

要求：
1. 提取的实体类型包括：Person（当事人/律师/法官）、Court（法院）、Law（法律法规）、Company（公司/机构）、Case（案件）、Provision（法律条文）
2. 提取实体间的关系，关系类型包括：INVOLVED_IN（参与）、HEARD_BY（审理）、REFERENCES（引用）、REPRESENTS（代理）、APPLIES_TO（适用于）、AMENDS（修订）、VIOLATES（违反）
3. 输出严格的JSON格式

输出格式：
{
    "entities": [
        {"name": "实体名称", "type": "实体类型", "properties": {"key": "value"}}
    ],
    "relations": [
        {"subject": "主体名称", "predicate": "关系类型", "object": "客体名称"}
    ]
}

法律文本：
"""


class EntityExtractionService:
    """LLM 法律实体关系抽取服务"""

    async def extract(self, text: str) -> dict[str, Any]:
        """从文本中抽取实体和关系"""
        if not text or not text.strip():
            return {"entities": [], "relations": [], "error": "文本为空"}

        try:
            from src.services.llm_helper import llm_helper

            prompt = EXTRACTION_PROMPT + text[:4000]

            response = await llm_helper.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000,
            )

            content = response.get("content", "")

            # 尝试解析JSON
            result = self._parse_extraction_result(content)
            return result

        except ImportError:
            logger.warning("llm_helper 不可用，使用规则抽取")
            return self._rule_based_extract(text)
        except Exception as e:
            logger.error(f"LLM 实体抽取失败: {e}")
            return self._rule_based_extract(text)

    def _parse_extraction_result(self, content: str) -> dict[str, Any]:
        """解析LLM输出的JSON"""
        try:
            # 尝试直接解析
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                result = json.loads(json_str)
                entities = result.get("entities", [])
                relations = result.get("relations", [])
                # 验证格式
                valid_entities = [
                    e for e in entities
                    if isinstance(e, dict) and e.get("name") and e.get("type")
                ]
                valid_relations = [
                    r for r in relations
                    if isinstance(r, dict) and r.get("subject") and r.get("predicate") and r.get("object")
                ]
                return {"entities": valid_entities, "relations": valid_relations}
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"JSON解析失败: {e}")
        return {"entities": [], "relations": [], "parse_error": "无法解析LLM输出"}

    def _rule_based_extract(self, text: str) -> dict[str, Any]:
        """基于规则的简单实体抽取（回退方案）"""
        import re
        entities: list[dict[str, Any]] = []
        relations: list[dict[str, Any]] = []

        # 法院
        courts = re.findall(r'[\u4e00-\u9fa5]+(?:人民法院|仲裁委员会)', text)
        for court in set(courts):
            entities.append({"name": court, "type": "Court", "properties": {}})

        # 法律法规
        laws = re.findall(r'《([\u4e00-\u9fa5]+(?:法|典|条例|规定|办法|细则))》', text)
        for law in set(laws):
            entities.append({"name": law, "type": "Law", "properties": {}})

        # 法律条文
        provisions = re.findall(r'第[\u4e00-\u9fa5零一二三四五六七八九十百千\d]+条', text)
        for p in set(provisions):
            entities.append({"name": p, "type": "Provision", "properties": {}})

        # 公司
        companies = re.findall(r'[\u4e00-\u9fa5]+(?:有限公司|股份有限公司|集团|公司)', text)
        for c in set(companies):
            if len(c) > 4:
                entities.append({"name": c, "type": "Company", "properties": {}})

        return {"entities": entities, "relations": relations, "method": "rule_based"}


entity_extraction_service = EntityExtractionService()
