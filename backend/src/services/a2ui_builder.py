"""
A2UI 面板数据生成器

从 Agent 回复中提取结构化数据，生成右侧智能分析面板的 A2UI 组件树。
"""

import re
from typing import Optional
from loguru import logger


def build_response_a2ui(agent_name: str, content: str, user_query: str = "") -> Optional[dict]:
    """
    从 Agent 回复内容中提取结构化数据，生成 A2UI 面板组件。
    
    Args:
        agent_name: Agent 名称
        content: Agent 回复内容
        user_query: 用户原始问题
        
    Returns:
        A2UI 组件树，或 None（如果内容太短不值得生成面板）
    """
    if not content or len(content) < 100:
        return None
    
    try:
        components = []
        
        # 1. 提取标题/要点（Markdown ## 或 **粗体** 标题）
        key_points = _extract_key_points(content)
        if key_points:
            components.append({
                "id": "key_points",
                "type": "card",
                "props": {
                    "title": "核心要点",
                    "icon": "sparkles",
                },
                "children": [{
                    "id": "key_points_list",
                    "type": "list",
                    "props": {
                        "items": key_points[:8],  # 最多 8 个要点
                        "ordered": True,
                    }
                }]
            })
        
        # 2. 提取法条/法规引用
        legal_refs = _extract_legal_references(content)
        if legal_refs:
            components.append({
                "id": "legal_refs",
                "type": "card",
                "props": {
                    "title": "相关法律法规",
                    "icon": "scale",
                },
                "children": [{
                    "id": "legal_refs_list",
                    "type": "list",
                    "props": {
                        "items": legal_refs[:6],
                        "ordered": False,
                    }
                }]
            })
        
        # 3. 提取风险提示
        risk_items = _extract_risk_items(content)
        if risk_items:
            components.append({
                "id": "risk_alerts",
                "type": "card",
                "props": {
                    "title": "风险提示",
                    "icon": "alert-triangle",
                    "variant": "warning",
                },
                "children": [{
                    "id": "risk_list",
                    "type": "list",
                    "props": {
                        "items": risk_items[:5],
                        "ordered": False,
                    }
                }]
            })
        
        # 4. 提取建议/下一步
        suggestions = _extract_suggestions(content)
        if suggestions:
            components.append({
                "id": "suggestions",
                "type": "card",
                "props": {
                    "title": "建议与下一步",
                    "icon": "check-circle",
                    "variant": "success",
                },
                "children": [{
                    "id": "suggestions_list",
                    "type": "list",
                    "props": {
                        "items": suggestions[:5],
                        "ordered": True,
                    }
                }]
            })
        
        # 5. 添加 Agent 信息卡
        components.insert(0, {
            "id": "agent_info",
            "type": "metric",
            "props": {
                "label": "处理Agent",
                "value": agent_name,
                "description": f"共提取 {len(key_points)} 个要点",
            }
        })
        
        if not components or len(components) <= 1:
            return None
        
        return {
            "a2ui": {
                "components": components
            }
        }
        
    except Exception as e:
        logger.warning(f"A2UI 面板数据生成失败: {e}")
        return None


def _extract_key_points(content: str) -> list:
    """提取关键要点（从 Markdown 标题和粗体文本中）"""
    points = []
    
    # 提取 ### 标题
    for match in re.finditer(r'^#{2,4}\s+(.+)$', content, re.MULTILINE):
        title = match.group(1).strip()
        title = re.sub(r'\*\*(.+?)\*\*', r'\1', title)  # 去掉粗体标记
        if title and len(title) > 2:
            points.append(title)
    
    # 如果没有标题，尝试提取 **粗体** 短语
    if not points:
        for match in re.finditer(r'\*\*(.+?)\*\*', content):
            text = match.group(1).strip()
            if 3 <= len(text) <= 50:
                points.append(text)
    
    # 去重
    seen = set()
    unique = []
    for p in points:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    
    return unique


def _extract_legal_references(content: str) -> list:
    """提取法律法规引用"""
    refs = []
    
    # 匹配《法律名称》
    for match in re.finditer(r'《(.+?)》', content):
        ref = match.group(1).strip()
        if ref and len(ref) > 2:
            refs.append(f"《{ref}》")
    
    # 匹配 "第X条" 引用
    for match in re.finditer(r'第\s*[一二三四五六七八九十百千\d]+\s*条', content):
        article = match.group(0).strip()
        if article not in refs:
            refs.append(article)
    
    # 去重
    seen = set()
    unique = []
    for r in refs:
        if r not in seen:
            seen.add(r)
            unique.append(r)
    
    return unique


def _extract_risk_items(content: str) -> list:
    """提取风险提示项"""
    risks = []
    
    risk_keywords = ['风险', '注意', '警告', '警惕', '隐患', '漏洞', '不利', '违约', '违法', '违规']
    
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
        # 匹配包含风险关键词的列表项
        if line.startswith(('-', '*', '•')) or re.match(r'^\d+[.、）)]', line):
            clean = re.sub(r'^[-*•\d.、）)]+\s*', '', line).strip()
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', clean)
            if any(kw in clean for kw in risk_keywords) and 5 <= len(clean) <= 200:
                risks.append(clean)
    
    return risks


def _extract_suggestions(content: str) -> list:
    """提取建议和下一步"""
    suggestions = []
    
    suggestion_keywords = ['建议', '推荐', '下一步', '应当', '需要', '可以考虑', '方案']
    
    in_suggestion_section = False
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # 检测建议段落
        if re.match(r'^#{2,4}.*(建议|方案|下一步|总结)', line):
            in_suggestion_section = True
            continue
        
        if in_suggestion_section and (line.startswith(('-', '*', '•')) or re.match(r'^\d+[.、）)]', line)):
            clean = re.sub(r'^[-*•\d.、）)]+\s*', '', line).strip()
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', clean)
            if clean and 5 <= len(clean) <= 200:
                suggestions.append(clean)
        elif in_suggestion_section and line.startswith('#'):
            in_suggestion_section = False
    
    # 如果没有找到建议段落，从全文搜索
    if not suggestions:
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith(('-', '*', '•')) or re.match(r'^\d+[.、）)]', line):
                clean = re.sub(r'^[-*•\d.、）)]+\s*', '', line).strip()
                clean = re.sub(r'\*\*(.+?)\*\*', r'\1', clean)
                if any(kw in clean for kw in suggestion_keywords) and 5 <= len(clean) <= 200:
                    suggestions.append(clean)
    
    return suggestions
