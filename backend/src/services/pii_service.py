import re
from typing import Tuple, List, Dict

class PIIService:
    """
    个人敏感信息 (PII) 识别与脱敏服务
    """
    
    # 简单的正则规则
    PATTERNS = {
        "PHONE": r'(13[0-9]|14[01456879]|15[0-35-9]|16[2567]|17[0-8]|18[0-9]|19[0-35-9])\d{8}',
        "ID_CARD": r'[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]',
        "EMAIL": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        "MONEY": r'([0-9]{1,3}(,[0-9]{3})*(\.[0-9]+)?|\d+(\.\d+)?)\s*(元|万元|亿元|CNY|USD)',
    }

    def __init__(self):
        self.redaction_map: Dict[str, str] = {}
        self.counter = 0

    def scrub(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        对文本进行脱敏
        Returns:
            (desensitized_text, recovery_map)
        """
        self.redaction_map = {}
        self.counter = 0
        
        scrubbed_text = text
        
        # 1. 处理手机号
        scrubbed_text = re.sub(self.PATTERNS["PHONE"], self._replace_phone, scrubbed_text)
        
        # 2. 处理身份证
        scrubbed_text = re.sub(self.PATTERNS["ID_CARD"], self._replace_id, scrubbed_text)
        
        # 3. 处理金额 (商业机密)
        scrubbed_text = re.sub(self.PATTERNS["MONEY"], self._replace_money, scrubbed_text)
        
        # 4. 简单的人名识别 (这里用非常简单的启发式，实际生产环境应使用NLP模型)
        # 假设 "张三"、"李四" 这种2-3字的名字出现在特定上下文中
        # 这里仅做演示，替换几个常见的名字
        demo_names = ["张三", "李四", "王五", "赵六", "陈总", "刘经理"]
        for name in demo_names:
            if name in scrubbed_text:
                placeholder = f"[PERSON_{self._get_next_id()}]"
                self.redaction_map[placeholder] = name
                scrubbed_text = scrubbed_text.replace(name, placeholder)

        return scrubbed_text, self.redaction_map

    def restore(self, text: str, recovery_map: Dict[str, str]) -> str:
        """
        还原脱敏文本
        """
        restored_text = text
        for placeholder, original in recovery_map.items():
            restored_text = restored_text.replace(placeholder, original)
        return restored_text

    def _get_next_id(self):
        self.counter += 1
        return self.counter

    def _replace_phone(self, match):
        original = match.group(0)
        placeholder = f"[PHONE_{self._get_next_id()}]"
        self.redaction_map[placeholder] = original
        return placeholder

    def _replace_id(self, match):
        original = match.group(0)
        placeholder = f"[ID_{self._get_next_id()}]"
        self.redaction_map[placeholder] = original
        return placeholder
        
    def _replace_money(self, match):
        original = match.group(0)
        placeholder = f"[AMOUNT_{self._get_next_id()}]"
        self.redaction_map[placeholder] = original
        return placeholder

pii_service = PIIService()
