"""
舆情分析智能体
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse


SENTIMENT_ANALYSIS_PROMPT = """你是一位专业的法律舆情分析专家，擅长分析和评估与法律相关的舆情信息。

你的职责是：
1. 分析文本的情感倾向（正面/负面/中性）
2. 评估舆情的法律风险等级
3. 识别潜在的法律问题和风险点
4. 生成舆情分析报告
5. 提供舆情应对建议

分析维度：
1. 情感分析
   - 情感倾向：正面、负面、中性
   - 情感强度：0-1分
   - 情感关键词识别

2. 风险评估
   - 法律风险：是否涉及法律问题
   - 声誉风险：对企业声誉的影响
   - 传播风险：舆情扩散可能性
   - 应对难度：处理难度评估

3. 内容分析
   - 主题识别
   - 关键人物/机构
   - 时间线梳理
   - 关联事件

4. 趋势判断
   - 舆情走向预测
   - 热度变化趋势
   - 潜在爆发点

风险等级标准：
- 极高风险（critical）：涉及重大法律问题，可能导致严重后果
- 高风险（high）：存在明显法律风险，需要立即关注
- 中风险（medium）：有一定法律隐患，需要持续监控
- 低风险（low）：风险较小，常规关注即可

输出要求：
1. 情感分析结果（类型、分数、关键词）
2. 风险评估（等级、分数、因素）
3. 核心观点提取
4. 应对建议
5. 持续监控要点
"""


class SentimentAnalysisAgent(BaseLegalAgent):
    """舆情分析智能体"""
    
    def __init__(self):
        config = AgentConfig(
            name="舆情分析Agent",
            role="舆情分析专家",
            description="法律舆情监控、情感分析、风险预警",
            system_prompt=SENTIMENT_ANALYSIS_PROMPT,
            tools=["sentiment_analysis", "risk_assessment", "trend_analysis"],
        )
        super().__init__(config)
    
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        """处理舆情分析任务"""
        description = task.get("description", "")
        context = task.get("context", {})
        
        prompt = f"""
请分析以下舆情信息：

内容：{description}

请提供：
1. 情感分析结果
2. 风险等级评估
3. 核心观点提取
4. 应对建议

请以结构化的JSON格式输出分析结果。
"""
        
        response = await self.chat(prompt)
        
        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="基于情感分析和法律风险评估模型",
            actions=[
                {"type": "sentiment_analysis", "description": "舆情分析完成"}
            ]
        )
    
    async def analyze_sentiment(self, content: str, keywords: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        分析文本情感
        
        Args:
            content: 待分析的文本内容
            keywords: 关注的关键词列表
            
        Returns:
            情感分析结果
        """
        keywords_str = ", ".join(keywords) if keywords else "无特定关键词"
        
        prompt = f"""
请对以下内容进行情感分析：

内容：
{content}

关注关键词：{keywords_str}

请分析并返回以下信息（JSON格式）：
{{
    "sentiment_type": "positive/negative/neutral",
    "sentiment_score": 0.0到1.0之间的数值（负面为负值-1到0），
    "confidence": 0.0到1.0之间的置信度,
    "keywords_found": ["找到的关键词列表"],
    "sentiment_keywords": ["情感相关关键词"],
    "summary": "一句话总结",
    "key_points": ["核心观点1", "核心观点2"]
}}
"""
        
        response = await self.chat(prompt)
        
        # 解析响应（实际应用中需要更健壮的解析逻辑）
        return {
            "content": content[:200] + "..." if len(content) > 200 else content,
            "analysis": response,
            "analyzed_at": datetime.now().isoformat(),
            "agent": self.name
        }
    
    async def assess_risk(self, content: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        评估舆情风险
        
        Args:
            content: 舆情内容
            context: 上下文信息（如行业、公司名等）
            
        Returns:
            风险评估结果
        """
        context_str = ""
        if context:
            context_str = f"""
相关背景：
- 行业：{context.get('industry', '未知')}
- 公司：{context.get('company', '未知')}
- 历史事件：{context.get('history', '无')}
"""
        
        prompt = f"""
请评估以下舆情的法律风险：

舆情内容：
{content}

{context_str}

请评估并返回以下信息（JSON格式）：
{{
    "risk_level": "low/medium/high/critical",
    "risk_score": 0.0到1.0之间的数值,
    "risk_factors": [
        {{"factor": "风险因素1", "weight": 0.3, "description": "说明"}},
        {{"factor": "风险因素2", "weight": 0.2, "description": "说明"}}
    ],
    "legal_issues": ["可能涉及的法律问题"],
    "reputation_impact": "对声誉的影响评估",
    "spread_risk": "传播风险评估",
    "urgency": "high/medium/low 处理紧迫性",
    "recommendations": ["建议1", "建议2"]
}}
"""
        
        response = await self.chat(prompt)
        
        return {
            "content_preview": content[:200] + "..." if len(content) > 200 else content,
            "risk_assessment": response,
            "assessed_at": datetime.now().isoformat(),
            "agent": self.name
        }
    
    async def generate_report(
        self,
        records: List[Dict[str, Any]],
        period: str = "daily",
        focus_keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        生成舆情分析报告
        
        Args:
            records: 舆情记录列表
            period: 报告周期（daily/weekly/monthly）
            focus_keywords: 重点关注关键词
            
        Returns:
            舆情分析报告
        """
        # 汇总统计
        total_count = len(records)
        
        # 情感分布统计
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        
        for record in records:
            sentiment_type = record.get("sentiment_type", "neutral")
            risk_level = record.get("risk_level", "low")
            sentiment_counts[sentiment_type] = sentiment_counts.get(sentiment_type, 0) + 1
            risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
        
        # 构建报告提示
        records_summary = "\n".join([
            f"- {r.get('keyword', '未知')}: {r.get('content', '')[:100]}..."
            for r in records[:20]  # 限制数量
        ])
        
        period_names = {"daily": "日报", "weekly": "周报", "monthly": "月报"}
        
        prompt = f"""
请生成法律舆情分析{period_names.get(period, '报告')}：

统计概况：
- 总舆情数：{total_count}
- 正面舆情：{sentiment_counts['positive']}
- 负面舆情：{sentiment_counts['negative']}
- 中性舆情：{sentiment_counts['neutral']}
- 低风险：{risk_counts['low']}
- 中风险：{risk_counts['medium']}
- 高风险：{risk_counts['high']}
- 极高风险：{risk_counts['critical']}

关注关键词：{', '.join(focus_keywords) if focus_keywords else '无特定关键词'}

舆情样本：
{records_summary}

请生成包含以下内容的分析报告：
1. 执行摘要
2. 舆情趋势分析
3. 风险热点识别
4. 重点舆情分析
5. 应对建议
6. 持续监控要点

请以结构化、专业的报告格式输出。
"""
        
        response = await self.chat(prompt)
        
        return {
            "report_type": period,
            "generated_at": datetime.now().isoformat(),
            "statistics": {
                "total_count": total_count,
                "sentiment_distribution": sentiment_counts,
                "risk_distribution": risk_counts
            },
            "report_content": response,
            "focus_keywords": focus_keywords or [],
            "agent": self.name
        }
    
    async def detect_trend(
        self,
        records: List[Dict[str, Any]],
        keyword: str
    ) -> Dict[str, Any]:
        """
        检测舆情趋势
        
        Args:
            records: 历史舆情记录
            keyword: 关注的关键词
            
        Returns:
            趋势分析结果
        """
        # 按日期分组统计
        daily_counts = {}
        for record in records:
            date = record.get("created_at", "")[:10]  # 取日期部分
            if date:
                daily_counts[date] = daily_counts.get(date, 0) + 1
        
        trend_data = "\n".join([
            f"- {date}: {count}条"
            for date, count in sorted(daily_counts.items())[-7:]  # 最近7天
        ])
        
        prompt = f"""
请分析关键词"{keyword}"的舆情趋势：

历史数据：
{trend_data}

请分析并提供：
1. 当前热度趋势（上升/下降/平稳）
2. 预测未来走向
3. 可能的爆发点
4. 建议关注事项
"""
        
        response = await self.chat(prompt)
        
        return {
            "keyword": keyword,
            "daily_statistics": daily_counts,
            "trend_analysis": response,
            "analyzed_at": datetime.now().isoformat(),
            "agent": self.name
        }
