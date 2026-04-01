"""
合同审查智能体
"""

from typing import Any, Dict
import json

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse
from src.prompts import load_prompt


_FALLBACK_PROMPT = "你是一位资深的合同审查专家，拥有丰富的合同法律实务经验。"


class ContractReviewAgent(BaseLegalAgent):
    """合同审查智能体"""
    
    def __init__(self):
        config = AgentConfig(
            name="合同审查Agent",
            role="合同审查专家",
            description="审查合同条款、识别风险、提供修改建议",
            system_prompt=load_prompt("agents/contract_reviewer.txt", fallback=_FALLBACK_PROMPT),
            temperature=0.3,  # 低温度确保稳定输出
            tools=["contract_parser", "template_compare"],
        )
        super().__init__(config)
    
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        """处理合同审查任务"""
        description = task.get("description", "")
        context = task.get("context") or {}
        contract_type = context.get("contract_type", "通用合同")

        # 构建针对合同类型的专项审查要求
        type_specific_guide = self._get_type_specific_guide(contract_type)

        # 构建审查提示
        prompt = f"""请对以下合同进行全面、系统的专业审查：

【合同类型】：{contract_type}

{type_specific_guide}

【合同文本】：
{description}

请严格按照系统提示中的三层审查框架（效力审查→核心条款→特殊条款）逐一检查，
并以规定的JSON格式输出完整审查结果。要求：
1. summary 字段不少于200字，概述合同主要内容、整体评价和核心风险
2. 至少从主体资格、权利义务、违约责任、争议解决、保密条款等5个维度分析
3. 每个风险点必须包含 legal_basis（引用具体法律条文）和 suggested_text（完整的修改后条款）
4. 列出合同缺少的重要条款到 missing_clauses 字段
5. 在 suggestions 中给出至少3条总体性改进建议
"""

        # 调用Agent
        response = await self.chat(prompt)

        # 尝试解析JSON结果
        review_result = self._parse_review_result(response)

        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="基于民法典合同编及相关法律法规进行三层系统性审查",
            citations=review_result.get("citations", []),
            actions=[
                {"type": "review_complete", "data": review_result}
            ],
            metadata=review_result
        )

    def _get_type_specific_guide(self, contract_type: str) -> str:
        """根据合同类型生成专项审查要点"""
        guides = {
            "买卖合同": "【专项审查要点】：标的物风险转移时点（民法典第604-617条）、质量标准和验收期限、瑕疵担保责任、所有权保留条款。",
            "租赁合同": "【专项审查要点】：租金调整机制、装修改造约定、优先购买权和优先续租权（民法典第726-734条）、转租条件。",
            "劳动合同": "【专项审查要点】：试用期约定合规性（劳动合同法第19-21条）、竞业限制补偿金标准、加班费计算、解除条件和经济补偿。",
            "服务合同": "【专项审查要点】：服务范围和SLA、知识产权归属、数据安全和隐私保护（个人信息保护法）、服务水平指标。",
            "借款合同": "【专项审查要点】：利率合规性（不超过LPR四倍）、还款方式、担保条款、提前还款权利、逾期利息约定。",
            "股权转让": "【专项审查要点】：估值方式和调整机制、对赌条款合法性、优先购买权、公司治理安排、竞业限制。",
            "合作协议": "【专项审查要点】：出资方式和比例、利润分配机制、决策机制、退出机制、知识产权归属。",
            "保密协议": "【专项审查要点】：保密信息范围界定、保密期限合理性、例外情形、违约救济措施、竞业限制关联。",
        }
        for key, guide in guides.items():
            if key in contract_type:
                return guide
        return "【审查要求】：请按照通用合同审查标准，重点关注核心条款完整性和风险防控。"
    
    def _parse_review_result(self, response: str) -> Dict[str, Any]:
        """解析审查结果，兼容增强后的输出格式"""
        import re

        try:
            # 尝试从响应中提取JSON（支持```json包裹的格式）
            # 先尝试 ```json ... ``` 格式
            code_block = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if code_block:
                result = json.loads(code_block.group(1))
            else:
                # 直接匹配最外层 JSON 对象
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError("未找到JSON内容")

            # 确保核心字段存在
            result.setdefault("summary", "")
            result.setdefault("risk_level", "medium")
            result.setdefault("risk_score", 0.5)
            result.setdefault("risks", [])
            result.setdefault("suggestions", [])
            result.setdefault("key_terms", {})
            result.setdefault("missing_clauses", [])

            return result
        except (json.JSONDecodeError, ValueError):
            pass

        # 如果解析失败，返回基本结构
        return {
            "summary": response[:800],
            "risk_level": "medium",
            "risk_score": 0.5,
            "risks": [],
            "suggestions": [],
            "key_terms": {},
            "missing_clauses": [],
        }
    
    async def quick_review(self, contract_text: str) -> Dict[str, Any]:
        """快速审查合同（简化版）"""
        prompt = f"""请快速审查以下合同，识别最重要的风险点：

{contract_text[:8000]}

请以JSON格式输出，包含：
1. "summary": 50字以内的总体评价
2. "risk_level": 整体风险等级（critical/high/medium/low）
3. "risks": 最重要的3-5个风险点，每个包含 title、level、description、suggestion
4. "missing_clauses": 缺少的重要条款列表

注意：每个风险点的description要引用具体的法律依据。"""

        response = await self.chat(prompt)
        result = self._parse_review_result(response)
        result["agent"] = self.name
        return result
