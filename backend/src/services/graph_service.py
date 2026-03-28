"""
图数据库服务
使用 CAMEL-AI 的 Neo4jGraph 进行图谱管理
"""

from typing import List, Dict, Any, Optional
from loguru import logger

from camel.storages import Neo4jGraph
from src.core.config import settings

class GraphService:
    """法务知识图谱服务"""
    
    def __init__(self):
        self.graph = None
        self._init_graph()
        
    def _init_graph(self):
        """初始化 Neo4j 客户端"""
        try:
            if not settings.NEO4J_URI:
                logger.warning("未配置 NEO4J_URI，图数据库功能不可用")
                return
                
            self.graph = Neo4jGraph(
                url=settings.NEO4J_URI,
                username=settings.NEO4J_USER,
                password=settings.NEO4J_PASSWORD,
            )
            logger.info(f"Neo4j 图数据库初始化成功: {settings.NEO4J_URI}")
        except Exception as e:
            logger.error(f"Neo4j 初始化失败: {e}")
            self.graph = None

    def add_legal_entities(self, case_info: Dict[str, Any], doc_id: str):
        """将清洗后的案件信息存入图谱"""
        if not self.graph:
            logger.warning("图数据库未连接，跳过实体入库")
            return
            
        try:
            # 1. 创建案件节点
            case_id_str = doc_id[:8]
            case_name = f"案件_{case_id_str}"
            
            # 2. 处理当事人
            parties = case_info.get("parties") or []
            for party in parties:
                # 添加 实体 -[参与]-> 案件 关系
                self.graph.add_triplet(party, "INVOLVED_IN", case_name)
                logger.debug(f"添加关系: ({party}) -[INVOLVED_IN]-> ({case_name})")
            
            # 3. 处理法院
            court_name = case_info.get("court_name")
            if court_name:
                self.graph.add_triplet(case_name, "HEARD_BY", court_name)
                logger.debug(f"添加关系: ({case_name}) -[HEARD_BY]-> ({court_name})")
                
            # 4. 处理法律条文
            provisions = case_info.get("legal_provisions") or []
            for provision in provisions:
                self.graph.add_triplet(case_name, "REFERENCES", provision)
                logger.debug(f"添加关系: ({case_name}) -[REFERENCES]-> ({provision})")
                
            logger.info(f"案件 {doc_id} 的实体关系已存入 Neo4j")
            
        except Exception as e:
            logger.error(f"存入图数据库失败: {e}")

    def query_graph(self, cypher_query: str) -> List[Dict[str, Any]]:
        """执行 Cypher 查询"""
        if not self.graph:
            return []
        try:
            return self.graph.query(cypher_query)
        except Exception as e:
            logger.error(f"Cypher 查询失败: {e}")
            return []

    def get_related_entities(self, entity_name: str, depth: int = 1) -> List[Dict[str, Any]]:
        """获取实体的关联实体及关系"""
        if not self.graph:
            return []
            
        # 构造 Cypher 查询获取 1-depth 步的关系
        query = f"""
        MATCH (n)-[r]-(m)
        WHERE n.name = '{entity_name}'
        RETURN n.name as source, type(r) as relation, m.name as target
        LIMIT 20
        """
        if depth > 1:
            query = f"""
            MATCH (n)-[r*1..{depth}]-(m)
            WHERE n.name = '{entity_name}'
            RETURN n.name as source, type(r[-1]) as relation, m.name as target
            LIMIT 50
            """
            
        return self.query_graph(query)

    def get_context_from_graph(self, entities: List[str]) -> str:
        """从图谱中提取实体及其关系的文本上下文"""
        if not self.graph or not entities:
            return ""
            
        all_triplets = []
        for entity in entities:
            triplets = self.get_related_entities(entity)
            all_triplets.extend(triplets)
            
        if not all_triplets:
            return ""
            
        # 去重并格式化
        seen = set()
        formatted_relations = []
        for t in all_triplets:
            rel_str = f"({t['source']}) -[{t['relation']}]-> ({t['target']})"
            if rel_str not in seen:
                seen.add(rel_str)
                formatted_relations.append(rel_str)
                
        context = "【图谱关联知识】\n" + "\n".join(formatted_relations)
        return context

    def get_graph_stats(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        if not self.graph:
            return {
                "available": False,
                "total_nodes": 0,
                "total_edges": 0,
                "node_types": {},
                "relation_types": {},
            }

        try:
            # 节点总数
            node_count_result = self.query_graph("MATCH (n) RETURN count(n) as cnt")
            total_nodes = node_count_result[0]["cnt"] if node_count_result else 0

            # 关系总数
            edge_count_result = self.query_graph("MATCH ()-[r]->() RETURN count(r) as cnt")
            total_edges = edge_count_result[0]["cnt"] if edge_count_result else 0

            # 节点标签分布
            label_result = self.query_graph(
                "MATCH (n) RETURN labels(n)[0] as label, count(n) as cnt ORDER BY cnt DESC LIMIT 10"
            )
            node_types = {r["label"]: r["cnt"] for r in label_result if r.get("label")}

            # 关系类型分布
            rel_result = self.query_graph(
                "MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as cnt ORDER BY cnt DESC LIMIT 10"
            )
            relation_types = {r["rel_type"]: r["cnt"] for r in rel_result if r.get("rel_type")}

            return {
                "available": True,
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "node_types": node_types,
                "relation_types": relation_types,
            }
        except Exception as e:
            logger.error(f"获取图谱统计失败: {e}")
            return {
                "available": False,
                "total_nodes": 0,
                "total_edges": 0,
                "node_types": {},
                "relation_types": {},
                "error": str(e),
            }

    def search_entities(self, keyword: str, depth: int = 1, limit: int = 30) -> Dict[str, Any]:
        """搜索实体及其关联（用于图谱可视化）"""
        if not self.graph:
            return {"nodes": [], "edges": [], "total": 0}

        try:
            # 模糊搜索包含关键词的实体
            if depth <= 1:
                query = f"""
                MATCH (n)-[r]-(m)
                WHERE n.name CONTAINS '{keyword}' OR m.name CONTAINS '{keyword}'
                RETURN n.name as source, labels(n)[0] as source_label, 
                       type(r) as relation, 
                       m.name as target, labels(m)[0] as target_label
                LIMIT {limit}
                """
            else:
                query = f"""
                MATCH path = (n)-[r*1..{depth}]-(m)
                WHERE n.name CONTAINS '{keyword}'
                WITH relationships(path) as rels, nodes(path) as ns
                UNWIND range(0, size(rels)-1) as i
                RETURN ns[i].name as source, labels(ns[i])[0] as source_label,
                       type(rels[i]) as relation,
                       ns[i+1].name as target, labels(ns[i+1])[0] as target_label
                LIMIT {limit}
                """

            results = self.query_graph(query)

            nodes = {}
            edges = []
            for r in results:
                source = r.get("source", "")
                target = r.get("target", "")
                relation = r.get("relation", "")
                source_label = r.get("source_label", "Entity")
                target_label = r.get("target_label", "Entity")

                if source and source not in nodes:
                    nodes[source] = {
                        "id": source,
                        "label": source,
                        "type": self._label_to_type(source_label, source),
                    }
                if target and target not in nodes:
                    nodes[target] = {
                        "id": target,
                        "label": target,
                        "type": self._label_to_type(target_label, target),
                    }
                if source and target:
                    edges.append({
                        "source": source,
                        "target": target,
                        "relation": relation,
                        "label": relation,
                    })

            return {
                "nodes": list(nodes.values()),
                "edges": edges,
                "total": len(nodes),
            }
        except Exception as e:
            logger.error(f"图谱搜索失败: {e}")
            return {"nodes": [], "edges": [], "total": 0, "error": str(e)}

    def _label_to_type(self, label: str, name: str = "") -> str:
        """将 Neo4j 标签转换为前端节点类型"""
        label_map = {
            "Law": "law",
            "Case": "document",
            "Court": "entity",
            "Person": "entity",
            "Company": "entity",
            "Provision": "law",
        }
        node_type = label_map.get(label, "entity")
        # 辅助推断
        if node_type == "entity" and name:
            if "法" in name or "条例" in name or "规定" in name:
                node_type = "law"
            elif "案" in name:
                node_type = "document"
        return node_type

# 全局单例
graph_service = GraphService()
