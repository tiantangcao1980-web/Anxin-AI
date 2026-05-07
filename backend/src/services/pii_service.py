import re
from collections.abc import Mapping, Sequence
from typing import Any, Final


class PIIService:
    """
    个人敏感信息 (PII) 识别与脱敏服务
    """

    # 简单的正则规则
    PATTERNS: Final[dict[str, str]] = {
        "PHONE": r"(13[0-9]|14[01456879]|15[0-35-9]|16[2567]|17[0-8]|18[0-9]|19[0-35-9])\d{8}",
        "ID_CARD": (
            r"[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))"
            r"(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]"
        ),
        "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "MONEY": r"([0-9]{1,3}(,[0-9]{3})*(\.[0-9]+)?|\d+(\.\d+)?)\s*(元|万元|亿元|CNY|USD)",
    }

    def __init__(self) -> None:
        self.redaction_map: dict[str, str] = {}
        self.counter = 0

    def scrub(self, text: str, scrub_money: bool = False) -> tuple[str, dict[str, str]]:
        """
        对文本进行脱敏

        Args:
            text: 待脱敏文本
            scrub_money: 是否脱敏金额（默认 False）
                - 合同起草/咨询场景中金额是必要业务信息，不应脱敏
                - 仅在明确需要保护商业机密时才传 True
        Returns:
            (desensitized_text, recovery_map)
        """
        self.redaction_map = {}
        self.counter = 0

        scrubbed_text = text

        # 1. 处理身份证（始终脱敏 — 强隐私信息）
        # 身份证号内部可能包含 1xx 号段片段，必须先于手机号处理。
        scrubbed_text = re.sub(self.PATTERNS["ID_CARD"], self._replace_id, scrubbed_text)

        # 2. 处理手机号（始终脱敏 — 避免泄露个人联系方式）
        scrubbed_text = re.sub(self.PATTERNS["PHONE"], self._replace_phone, scrubbed_text)

        # 3. 处理邮箱（始终脱敏 — 避免泄露个人联系方式）
        scrubbed_text = re.sub(self.PATTERNS["EMAIL"], self._replace_email, scrubbed_text)

        # 4. 金额脱敏 — 默认关闭（合同/咨询场景中金额是必要信息）
        # 用户在 settings 中显式开启"商业机密保护"时才脱敏
        if scrub_money:
            scrubbed_text = re.sub(self.PATTERNS["MONEY"], self._replace_money, scrubbed_text)

        # 5. 简单的人名识别 (这里用非常简单的启发式，实际生产环境应使用NLP模型)
        # 假设 "张三"、"李四" 这种2-3字的名字出现在特定上下文中
        # 这里仅做演示，替换几个常见的名字
        demo_names = ["张三", "李四", "王五", "赵六", "陈总", "刘经理"]
        for name in demo_names:
            if name in scrubbed_text:
                placeholder = f"[PERSON_{self._get_next_id()}]"
                self.redaction_map[placeholder] = name
                scrubbed_text = scrubbed_text.replace(name, placeholder)

        return scrubbed_text, self.redaction_map

    def scrub_for_output(self, value: Any) -> Any:
        """
        对检索/API 出口做无状态脱敏。

        与 scrub() 不同，这里不生成可还原 map，避免搜索结果、RAG sources、
        citation graph 等出口携带可逆敏感信息。
        """
        if isinstance(value, str):
            return self._mask_text(value)
        if isinstance(value, Mapping):
            return {key: self.scrub_for_output(item) for key, item in value.items()}
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return [self.scrub_for_output(item) for item in value]
        return value

    def restore(self, text: str, recovery_map: dict[str, str]) -> str:
        """
        还原脱敏文本
        """
        restored_text = text
        for placeholder, original in recovery_map.items():
            restored_text = restored_text.replace(placeholder, original)
        return restored_text

    def _get_next_id(self) -> int:
        self.counter += 1
        return self.counter

    def _replace_phone(self, match: re.Match[str]) -> str:
        original = match.group(0)
        placeholder = f"[PHONE_{self._get_next_id()}]"
        self.redaction_map[placeholder] = original
        return placeholder

    def _replace_id(self, match: re.Match[str]) -> str:
        original = match.group(0)
        placeholder = f"[ID_{self._get_next_id()}]"
        self.redaction_map[placeholder] = original
        return placeholder

    def _replace_email(self, match: re.Match[str]) -> str:
        original = match.group(0)
        placeholder = f"[EMAIL_{self._get_next_id()}]"
        self.redaction_map[placeholder] = original
        return placeholder

    def _replace_money(self, match: re.Match[str]) -> str:
        original = match.group(0)
        placeholder = f"[AMOUNT_{self._get_next_id()}]"
        self.redaction_map[placeholder] = original
        return placeholder

    def _mask_text(self, text: str) -> str:
        masked = re.sub(self.PATTERNS["ID_CARD"], self._mask_id_card, text)
        masked = re.sub(self.PATTERNS["PHONE"], self._mask_phone, masked)
        masked = re.sub(self.PATTERNS["EMAIL"], self._mask_email, masked)
        return masked

    @staticmethod
    def _mask_phone(match: re.Match[str]) -> str:
        phone = match.group(0)
        return f"{phone[:3]}****{phone[-4:]}"

    @staticmethod
    def _mask_id_card(match: re.Match[str]) -> str:
        id_card = match.group(0)
        return f"{id_card[:6]}********{id_card[-4:]}"

    @staticmethod
    def _mask_email(match: re.Match[str]) -> str:
        email = match.group(0)
        local, domain = email.split("@", 1)
        visible = local[:1] if local else "*"
        return f"{visible}***@{domain}"


pii_service = PIIService()
