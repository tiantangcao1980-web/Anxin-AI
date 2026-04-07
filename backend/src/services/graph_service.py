# -*- coding: utf-8 -*-
"""
图数据库服务
使用 CAMEL-AI 的 Neo4jGraph 进行图谱管理
"""

import atexit
import os
import time
from typing import Any, ClassVar, Optional, cast
from loguru import logger

try:
    from camel.storages import Neo4jGraph
except ImportError:
    Neo4jGraph = None
    logger.warning("camel-ai 未安装，图数据库功能不可用")

from src.core.config import settings


class GraphService:
    """法务知识图谱服务"""

    # ---- 进程内缓存 ----
    _cache: ClassVar[dict[str, Any]] = {}
    _cache_ts: ClassVar[dict[str, float]] = {}
    _CACHE_TTL = 300  # 5 分钟
    _INIT_RETRY_INTERVAL = 30  # 秒

    def _get_cached(self, key: str) -> Any | None:
        if key in self._cache and time.time() - self._cache_ts.get(key, 0) < self._CACHE_TTL:
            return self._cache[key]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = value
        self._cache_ts[key] = time.time()

    def _invalidate_cache(self) -> None:
        """清除全部缓存（写操作后调用）"""
        self._cache.clear()
        self._cache_ts.clear()

    def __init__(self) -> None:
        self._graph: Any | None = None
        self._last_init_attempt = 0.0
        atexit.register(self._close_sync)

    @property
    def graph(self) -> Any | None:
        self._ensure_graph()
        return self._graph

    @graph.setter
    def graph(self, value: Any | None) -> None:
        self._graph = value
        
    def _init_graph(self) -> None:
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
            logger.warning(f"Neo4j 当前不可用，图数据库功能将降级: {e}")
            self.graph = None

    def _ensure_graph(self) -> bool:
        """按需初始化 Neo4j 连接，失败时限流重试。"""
        if self._graph is not None:
            return True

        if os.environ.get("PYTEST_CURRENT_TEST"):
            return False

        if not settings.NEO4J_URI:
            return False

        now = time.time()
        if now - self._last_init_attempt < self._INIT_RETRY_INTERVAL:
            return False

        self._last_init_attempt = now
        self._init_graph()
        return self._graph is not None

    async def close(self) -> None:
        """显式关闭底层 Neo4j 连接，避免依赖析构器回收。"""
        graph = self._graph
        self._graph = None
        if graph is None:
            return

        try:
            driver = getattr(graph, "driver", None)
            if driver is not None and hasattr(driver, "close"):
                close_result = driver.close()
                if hasattr(close_result, "__await__"):
                    await close_result
            elif hasattr(graph, "close"):
                close_result = graph.close()
                if hasattr(close_result, "__await__"):
                    await close_result
            logger.info("Neo4j 图数据库连接已关闭")
        except Exception as e:
            logger.warning(f"关闭 Neo4j 图数据库连接失败: {e}")

    def _close_sync(self) -> None:
        """进程退出时的最佳努力关闭，覆盖未走应用生命周期的场景。"""
        graph = self._graph
        self._graph = None
        if graph is None:
            return
        try:
            driver = getattr(graph, "driver", None)
            if driver is not None and hasattr(driver, "close"):
                driver.close()
            elif hasattr(graph, "close"):
                graph.close()
        except Exception:
            pass

    def add_legal_entities(self, case_info: dict[str, Any], doc_id: str) -> None:
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

    def query_graph(self, cypher_query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """执行 Cypher 查询（支持参数化）"""
        if not self.graph:
            return []
        try:
            if params:
                return list(self.graph.query(cypher_query, params=params))
            return list(self.graph.query(cypher_query))
        except Exception as e:
            logger.error(f"Cypher 查询失败: {e}")
            return []

    def _find_entity_record(self, entity_name: str) -> dict[str, Any] | None:
        exact_query = """
        MATCH (n) WHERE n.name = $name
        RETURN n.name as name, labels(n) as labels, properties(n) as props
        LIMIT 1
        """
        exact_result = self.query_graph(exact_query, params={"name": entity_name})
        if exact_result:
            return exact_result[0]

        contains_query = """
        MATCH (n)
        WHERE n.name CONTAINS $keyword
        RETURN n.name as name, labels(n) as labels, properties(n) as props,
               CASE WHEN n.name STARTS WITH $keyword THEN 0 ELSE 1 END as prefix_rank,
               abs(size(n.name) - size($keyword)) as length_gap
        ORDER BY prefix_rank ASC, length_gap ASC, size(n.name) ASC, n.name ASC
        LIMIT 1
        """
        contains_result = self.query_graph(contains_query, params={"keyword": entity_name})
        if contains_result:
            return contains_result[0]

        return None

    def get_related_entities(self, entity_name: str, depth: int = 1) -> list[dict[str, Any]]:
        """获取实体的关联实体及关系"""
        if not self.graph:
            return []

        # 参数化查询防止 Cypher 注入
        if depth <= 1:
            query = """
            MATCH (n)-[r]-(m)
            WHERE n.name = $entity_name
            RETURN n.name as source, type(r) as relation, m.name as target
            LIMIT 20
            """
            return self.query_graph(query, params={"entity_name": entity_name})
        else:
            # depth 为整数，安全拼接；entity_name 走参数化
            safe_depth = max(1, min(int(depth), 10))
            query = f"""
            MATCH (n)-[r*1..{safe_depth}]-(m)
            WHERE n.name = $entity_name
            RETURN n.name as source, type(r[-1]) as relation, m.name as target
            LIMIT 50
            """
            return self.query_graph(query, params={"entity_name": entity_name})

    def get_context_from_graph(self, entities: list[str]) -> str:
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

    def get_graph_stats(self) -> dict[str, Any]:
        """获取图谱统计信息（带缓存）"""
        if not self.graph:
            return {
                "available": False,
                "total_nodes": 0,
                "total_edges": 0,
                "node_types": {},
                "relation_types": {},
            }

        cached = self._get_cached("graph_stats")
        if cached is not None:
            return cast(dict[str, Any], cached)

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

            result = {
                "available": True,
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "node_types": node_types,
                "relation_types": relation_types,
            }
            self._set_cache("graph_stats", result)
            return result
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

    def search_entities(self, keyword: str, depth: int = 1, limit: int = 30) -> dict[str, Any]:
        """搜索实体及其关联（用于图谱可视化，带缓存）"""
        if not self.graph:
            return {"nodes": [], "edges": [], "total": 0}

        cache_key = f"search:{keyword}:{depth}:{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cast(dict[str, Any], cached)

        try:
            # 参数化查询防止 Cypher 注入
            safe_limit = max(1, min(int(limit), 200))
            if depth <= 1:
                query = f"""
                MATCH (n)-[r]-(m)
                WHERE n.name CONTAINS $keyword OR m.name CONTAINS $keyword
                RETURN n.name as source, labels(n)[0] as source_label,
                       type(r) as relation,
                       m.name as target, labels(m)[0] as target_label
                LIMIT {safe_limit}
                """
                results = self.query_graph(query, params={"keyword": keyword})
            else:
                safe_depth = max(1, min(int(depth), 10))
                query = f"""
                MATCH path = (n)-[r*1..{safe_depth}]-(m)
                WHERE n.name CONTAINS $keyword
                WITH relationships(path) as rels, nodes(path) as ns
                UNWIND range(0, size(rels)-1) as i
                RETURN ns[i].name as source, labels(ns[i])[0] as source_label,
                       type(rels[i]) as relation,
                       ns[i+1].name as target, labels(ns[i+1])[0] as target_label
                LIMIT {safe_limit}
                """
                results = self.query_graph(query, params={"keyword": keyword})

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

            result = {
                "nodes": list(nodes.values()),
                "edges": edges,
                "total": len(nodes),
            }
            self._set_cache(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"图谱搜索失败: {e}")
            return {"nodes": [], "edges": [], "total": 0, "error": str(e)}

    # ================================================================
    # 搜索增强方法
    # ================================================================

    async def search_with_pagination(
        self, keyword: str, skip: int = 0, limit: int = 20, entity_type: Optional[str] = None
    ) -> dict[str, Any]:
        """分页搜索实体"""
        if not self.graph:
            return {"items": [], "total": 0, "skip": skip, "limit": limit}

        cache_key = f"search_page:{keyword}:{skip}:{limit}:{entity_type}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cast(dict[str, Any], cached)

        try:
            safe_skip = max(0, int(skip))
            safe_limit = max(1, min(int(limit), 200))

            # 构造 WHERE 条件
            where_clause = "WHERE n.name CONTAINS $keyword"
            if entity_type:
                where_clause += " AND $entity_type IN labels(n)"

            # 查询总数
            count_query = f"MATCH (n) {where_clause} RETURN count(n) as total"
            count_params: dict[str, Any] = {"keyword": keyword}
            if entity_type:
                count_params["entity_type"] = entity_type
            count_result = self.query_graph(count_query, params=count_params)
            total = count_result[0]["total"] if count_result else 0

            # 查询实体
            data_query = f"""
            MATCH (n) {where_clause}
            RETURN n.name as name, labels(n) as labels, properties(n) as props
            ORDER BY n.name
            SKIP {safe_skip} LIMIT {safe_limit}
            """
            data_result = self.query_graph(data_query, params=count_params)

            items = []
            for r in data_result:
                item_labels = r.get("labels", [])
                items.append({
                    "name": r.get("name", ""),
                    "type": item_labels[0] if item_labels else "Entity",
                    "labels": item_labels,
                    "properties": r.get("props", {}),
                })

            result = {"items": items, "total": total, "skip": safe_skip, "limit": safe_limit}
            self._set_cache(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"分页搜索失败: {e}")
            return {"items": [], "total": 0, "skip": skip, "limit": limit, "error": str(e)}

    async def get_entity_detail(self, entity_name: str) -> dict[str, Any]:
        """获取实体详情（属性 + 所有关系 + 关联文档）"""
        if not self.graph:
            return {"entity": None, "incoming_relations": [], "outgoing_relations": []}

        try:
            entity_data = self._find_entity_record(entity_name)
            if not entity_data:
                return {"entity": None, "incoming_relations": [], "outgoing_relations": []}

            entity_labels = entity_data.get("labels", [])
            resolved_name = entity_data.get("name", entity_name)
            entity = {
                "name": resolved_name,
                "type": entity_labels[0] if entity_labels else "Entity",
                "labels": entity_labels,
                "properties": entity_data.get("props", {}),
            }

            # 查询出关系
            out_query = """
            MATCH (n)-[r]->(m) WHERE n.name = $name
            RETURN type(r) as relation, m.name as target, labels(m) as target_labels,
                   properties(r) as rel_props
            LIMIT 100
            """
            out_result = self.query_graph(out_query, params={"name": resolved_name})
            outgoing = []
            for r in out_result:
                t_labels = r.get("target_labels", [])
                outgoing.append({
                    "relation": r.get("relation", ""),
                    "target": r.get("target", ""),
                    "target_type": t_labels[0] if t_labels else "Entity",
                    "properties": r.get("rel_props", {}),
                })

            # 查询入关系
            in_query = """
            MATCH (m)-[r]->(n) WHERE n.name = $name
            RETURN type(r) as relation, m.name as source, labels(m) as source_labels,
                   properties(r) as rel_props
            LIMIT 100
            """
            in_result = self.query_graph(in_query, params={"name": resolved_name})
            incoming = []
            for r in in_result:
                s_labels = r.get("source_labels", [])
                incoming.append({
                    "relation": r.get("relation", ""),
                    "source": r.get("source", ""),
                    "source_type": s_labels[0] if s_labels else "Entity",
                    "properties": r.get("rel_props", {}),
                })

            return {
                "name": entity["name"],
                "type": entity["type"],
                "properties": entity["properties"],
                "outEdges": [
                    {"target": item["target"], "label": item["relation"]}
                    for item in outgoing
                ],
                "inEdges": [
                    {"source": item["source"], "label": item["relation"]}
                    for item in incoming
                ],
                "entity": entity,
                "incoming_relations": incoming,
                "outgoing_relations": outgoing,
            }
        except Exception as e:
            logger.error(f"获取实体详情失败: {e}")
            return {"entity": None, "incoming_relations": [], "outgoing_relations": [], "error": str(e)}

    async def get_shortest_path(self, entity_a: str, entity_b: str, max_depth: int = 10) -> dict[str, Any]:
        """最短路径查询"""
        if not self.graph:
            return {"path_length": 0, "nodes": [], "relationships": []}

        try:
            safe_depth = max(1, min(int(max_depth), 20))
            query = f"""
            MATCH (a), (b)
            WHERE a.name = $name_a AND b.name = $name_b
            MATCH p = shortestPath((a)-[*..{safe_depth}]-(b))
            RETURN nodes(p) as path_nodes, relationships(p) as path_rels
            LIMIT 1
            """
            result = self.query_graph(query, params={"name_a": entity_a, "name_b": entity_b})
            if not result:
                return {"path_length": 0, "nodes": [], "relationships": [], "found": False}

            row = result[0]
            path_nodes_raw = row.get("path_nodes", [])
            path_rels_raw = row.get("path_rels", [])

            nodes = []
            for n in path_nodes_raw:
                if isinstance(n, dict):
                    nodes.append({
                        "name": n.get("name", ""),
                        "labels": n.get("labels", []),
                    })
                else:
                    nodes.append({"name": str(n)})

            relationships = []
            for r in path_rels_raw:
                if isinstance(r, dict):
                    relationships.append({
                        "type": r.get("type", ""),
                        "properties": {k: v for k, v in r.items() if k != "type"},
                    })
                else:
                    relationships.append({"type": str(r)})

            return {
                "path_length": len(relationships),
                "nodes": nodes,
                "relationships": relationships,
                "found": True,
            }
        except Exception as e:
            logger.error(f"最短路径查询失败: {e}")
            return {"path_length": 0, "nodes": [], "relationships": [], "error": str(e)}

    async def get_subgraph(self, entity_name: str, depth: int = 2, max_nodes: int = 50) -> dict[str, Any]:
        """子图提取（限制节点数防爆炸）"""
        if not self.graph:
            return {"center": entity_name, "nodes": [], "edges": []}

        try:
            safe_depth = max(1, min(int(depth), 5))
            safe_max = max(10, min(int(max_nodes), 200))

            query = f"""
            MATCH (center) WHERE center.name = $name
            CALL {{
                WITH center
                MATCH (center)-[r*1..{safe_depth}]-(m)
                RETURN DISTINCT m, r
                LIMIT {safe_max}
            }}
            WITH center, collect(DISTINCT m) as neighbors
            UNWIND neighbors as neighbor
            OPTIONAL MATCH (neighbor)-[rel]-(other)
            WHERE other = center OR other IN neighbors
            RETURN center.name as center_name, labels(center) as center_labels,
                   neighbor.name as node_name, labels(neighbor) as node_labels,
                   type(rel) as rel_type,
                   startNode(rel).name as rel_source, endNode(rel).name as rel_target
            LIMIT {safe_max * 3}
            """
            results = self.query_graph(query, params={"name": entity_name})

            # 回退方案：简化查询
            if not results:
                fallback_query = f"""
                MATCH (n {{name: $name}})-[r*1..{safe_depth}]-(m)
                WITH DISTINCT m, r
                LIMIT {safe_max}
                MATCH (m)-[rel]-(other)
                WHERE other.name = $name OR other = m
                RETURN m.name as node_name, labels(m) as node_labels,
                       type(rel) as rel_type,
                       startNode(rel).name as rel_source, endNode(rel).name as rel_target
                LIMIT {safe_max * 3}
                """
                results = self.query_graph(fallback_query, params={"name": entity_name})

            nodes_map: dict[str, dict[str, Any]] = {
                entity_name: {
                    "id": entity_name,
                    "label": entity_name,
                    "type": "entity",
                    "is_center": True,
                }
            }
            edges_set: set[str] = set()
            edges: list[dict[str, Any]] = []

            for r in results:
                node_name = r.get("node_name", "")
                node_labels = r.get("node_labels", [])
                if node_name and node_name not in nodes_map:
                    nodes_map[node_name] = {
                        "id": node_name,
                        "label": node_name,
                        "type": self._label_to_type(node_labels[0] if node_labels else "", node_name),
                    }

                rel_src = r.get("rel_source", "")
                rel_tgt = r.get("rel_target", "")
                rel_type = r.get("rel_type", "")
                if rel_src and rel_tgt and rel_type:
                    edge_key = f"{rel_src}-{rel_type}->{rel_tgt}"
                    if edge_key not in edges_set:
                        edges_set.add(edge_key)
                        edges.append({
                            "source": rel_src,
                            "target": rel_tgt,
                            "relation": rel_type,
                            "label": rel_type,
                        })

            return {
                "center": entity_name,
                "nodes": list(nodes_map.values()),
                "edges": edges,
            }
        except Exception as e:
            logger.error(f"子图提取失败: {e}")
            return {"center": entity_name, "nodes": [], "edges": [], "error": str(e)}

    async def batch_import_entities(self, entities: list[dict[str, Any]]) -> dict[str, Any]:
        """批量导入三元组"""
        if not self.graph:
            return {"imported": 0, "errors": ["图数据库未连接"]}

        imported = 0
        errors = []
        try:
            for idx, ent in enumerate(entities):
                subject = ent.get("subject", "").strip()
                predicate = ent.get("predicate", "").strip()
                obj = ent.get("object", "").strip()

                if not subject or not predicate or not obj:
                    errors.append(f"第 {idx + 1} 条三元组缺少 subject/predicate/object")
                    continue

                try:
                    self.graph.add_triplet(subject, predicate, obj)
                    imported += 1
                except Exception as inner_e:
                    errors.append(f"第 {idx + 1} 条导入失败: {str(inner_e)}")

            # 写操作后清缓存
            self._invalidate_cache()
            logger.info(f"批量导入完成: 成功 {imported} 条, 失败 {len(errors)} 条")
            return {"imported": imported, "errors": errors}
        except Exception as e:
            logger.error(f"批量导入失败: {e}")
            return {"imported": imported, "errors": errors + [str(e)]}

    async def get_entity_types(self) -> list[dict[str, Any]]:
        """获取所有实体类型列表（带缓存）"""
        if not self.graph:
            return []

        cached = self._get_cached("entity_types")
        if cached is not None:
            return cast(list[dict[str, Any]], cached)

        try:
            query = """
            MATCH (n)
            WITH labels(n)[0] as label
            WHERE label IS NOT NULL
            RETURN label as type, count(*) as count
            ORDER BY count DESC
            """
            results = self.query_graph(query)

            # 为每种类型分配颜色
            color_palette = [
                "#22c55e", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6",
                "#06b6d4", "#ec4899", "#14b8a6", "#f97316", "#6366f1",
            ]
            types_list = []
            for idx, r in enumerate(results):
                types_list.append({
                    "type": r.get("type", "Unknown"),
                    "count": r.get("count", 0),
                    "color": color_palette[idx % len(color_palette)],
                })

            self._set_cache("entity_types", types_list)
            return types_list
        except Exception as e:
            logger.error(f"获取实体类型失败: {e}")
            return []

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

    async def create_entity(self, name: str, entity_type: str = "Entity", properties: dict[str, Any] | None = None) -> dict[str, Any]:
        """创建实体节点"""
        if not self.graph:
            return {"success": False, "error": "图数据库未连接"}
        try:
            props = properties or {}
            props["name"] = name
            props_str = ", ".join([f"n.{k} = ${k}" for k in props.keys()])
            query = f"CREATE (n:{entity_type}) SET {props_str} RETURN n.name as name, labels(n) as labels"
            result = self.query_graph(query, params=props)
            self._invalidate_cache()
            return {"success": True, "name": name, "type": entity_type}
        except Exception as e:
            logger.error(f"创建实体失败: {e}")
            return {"success": False, "error": str(e)}

    async def update_entity(self, name: str, properties: dict[str, Any]) -> dict[str, Any]:
        """更新实体属性"""
        if not self.graph:
            return {"success": False, "error": "图数据库未连接"}
        try:
            set_clauses = []
            params = {"name": name}
            for k, v in properties.items():
                if k == "name":
                    continue
                param_key = f"prop_{k}"
                set_clauses.append(f"n.{k} = ${param_key}")
                params[param_key] = v
            if not set_clauses:
                return {"success": True, "message": "无需更新"}
            query = f"MATCH (n) WHERE n.name = $name SET {', '.join(set_clauses)} RETURN n.name as name"
            result = self.query_graph(query, params=params)
            self._invalidate_cache()
            return {"success": bool(result), "name": name}
        except Exception as e:
            logger.error(f"更新实体失败: {e}")
            return {"success": False, "error": str(e)}

    async def delete_entity(self, name: str) -> dict[str, Any]:
        """删除实体及其所有关系"""
        if not self.graph:
            return {"success": False, "error": "图数据库未连接"}
        try:
            # 先获取关联数
            count_query = "MATCH (n {name: $name})-[r]-() RETURN count(r) as cnt"
            count_result = self.query_graph(count_query, params={"name": name})
            relation_count = count_result[0]["cnt"] if count_result else 0

            query = "MATCH (n {name: $name}) DETACH DELETE n RETURN count(*) as deleted"
            result = self.query_graph(query, params={"name": name})
            deleted = result[0]["deleted"] if result else 0
            self._invalidate_cache()
            return {"success": deleted > 0, "deleted_relations": relation_count}
        except Exception as e:
            logger.error(f"删除实体失败: {e}")
            return {"success": False, "error": str(e)}

    async def create_relation(self, subject: str, predicate: str, obj: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        """创建关系"""
        if not self.graph:
            return {"success": False, "error": "图数据库未连接"}
        try:
            self.graph.add_triplet(subject, predicate, obj)
            self._invalidate_cache()
            return {"success": True, "subject": subject, "predicate": predicate, "object": obj}
        except Exception as e:
            logger.error(f"创建关系失败: {e}")
            return {"success": False, "error": str(e)}

    async def delete_relation(self, subject: str, predicate: str, obj: str) -> dict[str, Any]:
        """删除指定关系"""
        if not self.graph:
            return {"success": False, "error": "图数据库未连接"}
        try:
            query = """
            MATCH (a {name: $subject})-[r]->(b {name: $object})
            WHERE type(r) = $predicate
            DELETE r
            RETURN count(*) as deleted
            """
            result = self.query_graph(query, params={"subject": subject, "predicate": predicate, "object": obj})
            deleted = result[0]["deleted"] if result else 0
            self._invalidate_cache()
            return {"success": deleted > 0, "deleted": deleted}
        except Exception as e:
            logger.error(f"删除关系失败: {e}")
            return {"success": False, "error": str(e)}

    async def export_triples(self, entity_type: str | None = None, limit: int = 10000) -> list[dict[str, str]]:
        """导出所有三元组为列表"""
        if not self.graph:
            return []
        try:
            safe_limit = max(1, min(int(limit), 50000))
            if entity_type:
                query = f"""
                MATCH (a:{entity_type})-[r]->(b)
                RETURN a.name as subject, type(r) as predicate, b.name as object
                LIMIT {safe_limit}
                """
            else:
                query = f"""
                MATCH (a)-[r]->(b)
                RETURN a.name as subject, type(r) as predicate, b.name as object
                LIMIT {safe_limit}
                """
            results = self.query_graph(query)
            return [{"subject": r["subject"], "predicate": r["predicate"], "object": r["object"]} for r in results if r.get("subject") and r.get("object")]
        except Exception as e:
            logger.error(f"导出三元组失败: {e}")
            return []

# 全局单例
graph_service = GraphService()
