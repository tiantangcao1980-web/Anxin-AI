"""
法规研究智能体
"""

import re
import json
from typing import Any, Dict, List

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse


LEGAL_RESEARCH_PROMPT = """你是一位专业的法律研究员，精通法律法规检索和判例分析。

你的职责是：
1. 检索相关法律法规
2. 分析司法判例
3. 研究法律问题
4. 提供法律依据
5. 撰写法律研究报告

研究范围：
- 法律法规：宪法、法律、行政法规、地方性法规、规章
- 司法解释：最高人民法院、最高人民检察院的司法解释
- 指导案例：最高人民法院发布的指导性案例
- 典型判例：各级法院的典型判决
- 行业规范：行业协会规范性文件

研究方法：
1. 关键词检索：根据问题提取关键法律概念
2. 体系检索：从法律体系角度全面检索
3. 判例检索：查找相关判例和裁判观点
4. 学理研究：参考法学理论和学术观点

输出要求：
1. 列明具体法律条文（法律名称、条款号、内容）
2. 引用相关判例（案号、裁判要点）
3. 提供法律分析意见
4. 给出适用建议

注意事项：
- 确保引用的法律法规现行有效
- 注意法律的时效性和适用范围
- 区分强制性规定和任意性规定
- 考虑不同法域的适用差异
"""


DEEP_RESEARCH_PROMPT = """你是一位资深的法律科学家，擅长处理复杂的法律研究课题。
你不仅能检索法律条文，还能深入分析法理逻辑、法律演进、跨区域比较以及最新的司法趋势。

你的任务是进行“深度研究”，这要求：
1. **多维度剖析**：从实体法、程序法、比较法、法理学四个维度展开。
2. **逻辑穿透**：分析裁判思路背后的法理依据，而不只是罗列条文。
3. **时效捕捉**：特别关注近 6 个月内的最高法指导案例或最新立法动向。
4. **风险预测**：基于当前司法环境，预测该法律问题的裁判不确定性。

输出必须包含：
- 【研究摘要】
- 【核心法源】（包含法律、法规、司法解释）
- 【深度法理分析】（探讨争议核心）
- 【类案研究】（提炼裁判规则）
- 【合规与实操建议】
"""


class LegalResearchAgent(BaseLegalAgent):
    """法规研究智能体"""
    
    def __init__(self):
        config = AgentConfig(
            name="法规研究Agent",
            role="法律研究员",
            description="法律法规检索、判例分析、法律研究",
            system_prompt=LEGAL_RESEARCH_PROMPT,
            tools=["legal_database", "case_search", "knowledge_search", "web_search"],
        )
        super().__init__(config)
    
    async def deep_research(self, topic: str, context: Dict[str, Any] = None) -> AgentResponse:
        """执行深度法律研究"""
        # 切换到深度提示词
        original_prompt = self.config.system_prompt
        self.config.system_prompt = DEEP_RESEARCH_PROMPT
        
        try:
            prompt = f"""
请对以下课题进行深度法律研究：

研究课题：{topic}

上下文信息：{json.dumps(context) if context else "无"}

要求：
1. 深入检索相关法律体系。
2. 分析至少 3 个相关的典型或指导性判例。
3. 给出前瞻性的风险提示。
"""
            response = await self.chat(prompt)
            citations = self._extract_citations(response)
            
            return AgentResponse(
                agent_name=self.name,
                content=response,
                reasoning="执行深度研究模式，结合多维法理分析与实时案例库",
                citations=citations,
                actions=[
                    {"type": "deep_research_complete", "description": "深度法律研究已完成"}
                ]
            )
        finally:
            # 还原提示词
            self.config.system_prompt = original_prompt

    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        """处理法律研究任务"""
        description = task.get("description", "")
        context = task.get("context", {})
        
        # 构建研究提示
        prompt = f"""
请对以下法律问题进行研究：

研究问题：{description}

请提供：
1. 相关法律法规（列明法律名称、条款号、具体内容）
2. 相关司法解释（如有）
3. 典型判例分析（案号、裁判要点）
4. 法律适用分析
5. 结论和建议

请确保引用准确，注明法律法规的时效性。
"""
        
        # 调用Agent
        response = await self.chat(prompt)
        
        # 提取引用
        citations = self._extract_citations(response)
        
        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="基于法律法规数据库和判例库进行综合研究",
            citations=citations,
            actions=[
                {"type": "research_complete", "description": "法律研究完成"}
            ]
        )
    
    def _extract_citations(self, response: str) -> List[Dict]:
        """提取法律引用"""
        citations = []
        
        # 简单的引用提取逻辑
        # 实际应用中需要更复杂的NLP处理
        import re
        
        # 匹配《法律名称》第X条
        law_pattern = r'《([^》]+)》[第]*(\d+)[条款]'
        for match in re.finditer(law_pattern, response):
            citations.append({
                "type": "law",
                "name": match.group(1),
                "article": match.group(2),
            })
        
        # 匹配案号
        case_pattern = r'\((\d{4})\)[^号]*号'
        for match in re.finditer(case_pattern, response):
            citations.append({
                "type": "case",
                "case_number": match.group(0),
            })
        
        return citations
    
    async def search_laws(self, keywords: List[str]) -> Dict[str, Any]:
        """检索法律法规"""
        keywords_str = "、".join(keywords)
        prompt = f"""
请检索与以下关键词相关的法律法规：

关键词：{keywords_str}

请列出：
1. 相关法律（法律名称、实施日期、主要条款）
2. 相关行政法规
3. 相关司法解释
4. 相关部门规章

按相关性排序，每类列出最相关的3-5部。
"""
        response = await self.chat(prompt)
        
        return {
            "keywords": keywords,
            "results": response,
            "agent": self.name
        }
    
    async def analyze_case(self, case_number: str) -> Dict[str, Any]:
        """分析判例"""
        prompt = f"""
请分析案号为 "{case_number}" 的判例：

1. 基本案情
2. 争议焦点
3. 裁判要点
4. 法律适用
5. 参考价值

请提供详细分析。
"""
        response = await self.chat(prompt)
        
        return {
            "case_number": case_number,
            "analysis": response,
            "agent": self.name
        }
