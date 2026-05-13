# AI法律助手 - 分层记忆与进化能力架构设计

## 1. 架构概述

本文档描述基于 OpenClaw、Camel AI 和 Anthropic Agent Team 研究成果的**三层记忆架构**和**持续进化机制**。

### 1.1 核心理念

```
┌────────────────────────────────────────────────────────────────┐
│                    持续进化型多智能体系统                        │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              元学习层 (Meta-Learning Layer)            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │   │
│  │  │ 反馈处理管道  │→│ 经验提取器   │→│ 策略优化器  │  │   │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  │   │
│  └────────────────────────────────────────────────────────┘   │
│                           ↓↑                                   │
│  ┌────────────────────────────────────────────────────────┐   │
│  │               三层记忆架构 (Memory System)              │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │   │
│  │  │ 语义记忆     │  │ 情景记忆      │  │ 工作记忆      │  │   │
│  │  │ (长期)      │  │ (中期)       │  │ (短期)        │  │   │
│  │  │ 知识图谱    │  │ 案例库       │  │ 会话上下文    │  │   │
│  │  │ Qdrant+PG  │  │ Qdrant+PG    │  │ Redis         │  │   │
│  │  └─────────────┘  └──────────────┘  └───────────────┘  │   │
│  └────────────────────────────────────────────────────────┘   │
│                           ↓↑                                   │
│  ┌────────────────────────────────────────────────────────┐   │
│  │            多智能体工作层 (Agent Workforce)             │   │
│  │  LegalAgent │ ContractAgent │ DueDiligenceAgent ...   │   │
│  └────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. 三层记忆架构

### 2.1 记忆层次定义

#### 2.1.1 语义记忆 (Semantic Memory) - 长期知识

**存储内容**:
- 法律概念、法规条文、判例摘要
- 合同条款模板、法律文书格式
- 行业知识、专业术语定义

**存储结构**:
```python
class SemanticMemory:
    """语义记忆 - 静态知识存储"""

    memory_id: str
    knowledge_type: Literal["statute", "case", "template", "concept"]
    content: str
    embedding: List[float]  # 向量嵌入

    # 知识关联
    related_concepts: List[str]  # 知识图谱节点
    citations: List[Dict]  # 引用来源

    # 访问统计
    access_count: int
    last_accessed: datetime
    confidence_score: float  # 可信度 0-1
```

**存储位置**: `Qdrant (semantic_memory)` + `PostgreSQL (knowledge_graph)`

**检索策略**:
- 向量相似度搜索 (Embedding Similarity)
- 知识图谱关联推理 (Graph Traversal)
- 混合排序: `score = 0.7 * similarity + 0.3 * confidence * access_frequency`

---

#### 2.1.2 情景记忆 (Episodic Memory) - 中期经验

**存储内容**:
- 历史案件处理过程
- 用户反馈和结果评分
- Agent 执行轨迹和决策路径
- 成功/失败的模式

**存储结构**:
```python
class EpisodicMemory:
    """情景记忆 - 动态经验存储"""

    memory_id: str
    session_id: str  # 所属会话

    # 任务信息
    task_description: str
    task_type: str  # "contract_review", "case_analysis", etc.
    agents_involved: List[str]  # 参与的 Agent 列表

    # 执行过程
    execution_trace: List[Dict]  # DAG 执行轨迹
    reasoning_chain: List[str]  # 推理链

    # 结果与反馈
    result_summary: str
    user_rating: int  # 1-5 分
    user_feedback: str
    success_metrics: Dict  # 效率、质量指标

    # 进化标记
    is_successful: bool
    failure_reason: Optional[str]
    learned_patterns: List[str]  # 提取的模式

    # 时间戳
    created_at: datetime
    last_accessed: datetime
```

**存储位置**: `Qdrant (episodic_memory)` + `PostgreSQL (episodes)`

**检索策略**:
- 任务相似度匹配
- 成功案例优先过滤 (`rating >= 4` 或 `is_successful == true`)
- 适应性重排序: `score = similarity * (1 + success_rate)`

---

#### 2.1.3 工作记忆 (Working Memory) - 短期上下文

**存储内容**:
- 当前会话的对话历史
- 正在进行的任务状态
- 临时变量和中间结果
- Agent 间共享状态

**存储结构**:
```python
class WorkingMemory:
    """工作记忆 - 会话级临时存储"""

    session_id: str
    user_id: str

    # 对话上下文
    messages: List[Dict]  # 最近 N 条消息
    current_context: Dict  # 当前理解的问题上下文

    # 任务状态
    active_tasks: List[Dict]  # 正在进行的任务
    task_stack: List[str]  # 任务调用栈

    # Agent 状态
    agent_states: Dict[str, Dict]  # 各 Agent 的临时状态
    shared_variables: Dict  # Agent 间共享变量

    # 临时缓存
    retrieved_memories: Dict  # 已检索的相关记忆
    draft_content: str  # 草稿内容

    # TTL 配置
    expires_at: datetime  # 自动过期时间
```

**存储位置**: `Redis (working_memory:{session_id})`

**生命周期**:
- 创建: 会话开始
- 更新: 每次交互
- 过期: 会话结束 24 小时后 (TTL)
- 归档: 会话结束时,有价值内容 → 情景记忆

---

### 2.2 记忆交互流程

#### 2.2.1 多层记忆检索流程

```python
class MultiTierMemoryRetrieval:
    """多层记忆检索器"""

    async def retrieve(
        self,
        query: str,
        session_id: str,
        context: Dict
    ) -> MemoryRetrievalResult:
        """
        跨层检索策略
        """
        result = MemoryRetrievalResult()

        # 1️⃣ 工作记忆层 (最快,直接返回)
        result.working = await self._retrieve_working(session_id)
        if result.working.is_sufficient:
            return result

        # 2️⃣ 情景记忆层 (中速,返回相关案例)
        result.episodic = await self._retrieve_episodic(
            query=query,
            task_type=context.get("task_type"),
            top_k=3,
            min_rating=4  # 优先高分案例
        )

        # 3️⃣ 语义记忆层 (慢速,返回知识)
        result.semantic = await self._retrieve_semantic(
            query=query,
            knowledge_types=context.get("knowledge_types", []),
            top_k=5
        )

        # 4️⃣ 跨层融合与排序
        result = await self._fuse_and_rank(result, query)

        # 5️⃣ 缓存到工作记忆
        await self._cache_to_working(session_id, result)

        return result
```

#### 2.2.2 记忆写入流程

```python
class MemoryWriter:
    """记忆写入器"""

    async def write_episode(
        self,
        session_id: str,
        task_data: Dict,
        result: Dict,
        feedback: Dict
    ):
        """
        将完成的任务写入情景记忆
        """
        # 1. 从工作记忆收集完整上下文
        working_context = await self._get_working_context(session_id)

        # 2. 构建情景记忆对象
        episode = EpisodicMemory(
            session_id=session_id,
            task_description=task_data["description"],
            execution_trace=working_context["execution_trace"],
            result_summary=result["summary"],
            user_rating=feedback.get("rating", 0),
            success_metrics=self._compute_metrics(working_context, result)
        )

        # 3. 提取学习模式
        episode.learned_patterns = await self._extract_patterns(episode)

        # 4. 写入情景记忆
        await self.episodic_store.add(episode)

        # 5. 更新语义记忆 (如果发现新知识)
        if episode.is_successful:
            await self._update_semantic_memory(episode)
```

---

## 3. 进化能力架构

### 3.1 进化循环

```
┌───────────────────────────────────────────────────────────┐
│                    进化循环 (Evolution Loop)              │
│                                                           │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│  │  用户    │───→│  Agent   │───→│  结果    │           │
│  │  请求    │    │  执行    │    │  生成    │           │
│  └──────────┘    └──────────┘    └──────────┘           │
│       │                               │                  │
│       │                               ↓                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│  │  持续    │←──│  经验    │←──│  反馈    │           │
│  │  优化    │    │  提取    │    │  收集    │           │
│  └──────────┘    └──────────┘    └──────────┘           │
│       │                               │                  │
│       └───────────────┬───────────────┘                  │
│                       ↓                                  │
│              ┌──────────────┐                            │
│              │  策略更新    │                            │
│              │  Agent选择   │                            │
│              │  DAG优化     │                            │
│              └──────────────┘                            │
└───────────────────────────────────────────────────────────┘
```

### 3.2 反馈处理管道

```python
class FeedbackPipeline:
    """反馈处理管道"""

    async def process_feedback(
        self,
        session_id: str,
        message_id: str,
        feedback: Dict
    ):
        """
        处理用户反馈,触发进化流程
        """
        # 1. 验证反馈
        if not self._validate_feedback(feedback):
            return

        # 2. 更新情景记忆
        episode_id = await self.episodic_memory.update_feedback(
            message_id=message_id,
            rating=feedback["rating"],
            comment=feedback.get("comment", "")
        )

        # 3. 触发经验提取 (异步)
        asyncio.create_task(
            self.experience_extractor.extract(episode_id)
        )

        # 4. 发布反馈事件
        await self.event_bus.publish("feedback.received", {
            "session_id": session_id,
            "episode_id": episode_id,
            "feedback": feedback
        })
```

### 3.3 经验提取器

```python
class ExperienceExtractor:
    """经验提取器 - 从历史案例中学习"""

    async def extract(self, episode_id: str) -> List[Pattern]:
        """
        从单个案例中提取可重用的模式
        """
        episode = await self.episodic_memory.get(episode_id)

        patterns = []

        # 1. 成功模式提取
        if episode.is_successful and episode.user_rating >= 4:
            patterns.extend(await self._extract_success_patterns(episode))

        # 2. 失败模式提取
        if not episode.is_successful or episode.user_rating <= 2:
            patterns.extend(await self._extract_failure_patterns(episode))

        # 3. Agent 协作模式
        patterns.extend(await self._extract_collaboration_patterns(episode))

        # 4. 优化建议模式
        patterns.extend(await self._extract_optimization_patterns(episode))

        # 5. 存储模式到策略库
        for pattern in patterns:
            await self.pattern_store.add(pattern)

        return patterns

    async def _extract_success_patterns(self, episode: Episode) -> List[Pattern]:
        """
        提取成功模式
        """
        patterns = []

        # 分析 DAG 执行效率
        dag_pattern = Pattern(
            type="dag_optimization",
            task_type=episode.task_type,
            description=f"高效的 {episode.task_type} DAG 配置",
            confidence=min(episode.user_rating / 5, 1.0),
            data={
                "agents_used": episode.agents_involved,
                "execution_time": episode.execution_time,
                "agent_sequence": episode.execution_trace["agent_sequence"],
                "parallel_tasks": episode.execution_trace["parallel_groups"]
            }
        )
        patterns.append(dag_pattern)

        # 分析推理链质量
        if episode.reasoning_chain:
            reasoning_pattern = Pattern(
                type="reasoning_template",
                task_type=episode.task_type,
                description=f"有效的 {episode.task_type} 推理路径",
                confidence=min(episode.user_rating / 5, 1.0),
                data={
                    "reasoning_steps": episode.reasoning_chain,
                    "key_decisions": episode.execution_trace["decisions"]
                }
            )
            patterns.append(reasoning_pattern)

        return patterns
```

### 3.4 策略优化器

```python
class PolicyOptimizer:
    """策略优化器 - 基于经验优化决策"""

    async def optimize_agent_selection(
        self,
        task_description: str,
        task_type: str
    ) -> List[str]:
        """
        基于历史经验优化 Agent 选择
        """
        # 1. 检索相关成功案例
        successful_episodes = await self.episodic_memory.retrieve_similar(
            task_description=task_description,
            task_type=task_type,
            min_rating=4,
            top_k=10
        )

        if not successful_episodes:
            # 无历史经验,使用默认策略
            return self._get_default_agents(task_type)

        # 2. 统计最常用的 Agent 组合
        agent_combinations = Counter()
        for episode in successful_episodes:
            agents_tuple = tuple(sorted(episode.agents_involved))
            agent_combinations[agents_tuple] += episode.user_rating

        # 3. 返回评分最高的组合
        best_agents = list(agent_combinations.most_common(1)[0][0])

        self.logger.info(
            f"策略优化: 为 {task_type} 选择 Agent {best_agents} "
            f"(基于 {len(successful_episodes)} 个成功案例)"
        )

        return best_agents

    async def optimize_dag_structure(
        self,
        task_description: str,
        task_type: str,
        agents: List[str]
    ) -> DAGStructure:
        """
        基于历史经验优化 DAG 结构
        """
        # 1. 检索相关案例
        episodes = await self.episodic_memory.retrieve_similar(
            task_description=task_description,
            task_type=task_type,
            min_rating=3,
            top_k=5
        )

        if not episodes:
            return self._default_dag(agents)

        # 2. 分析最佳 DAG 结构
        best_episode = max(episodes, key=lambda e: e.success_metrics.get("efficiency", 0))

        # 3. 提取 DAG 模式
        dag_structure = DAGStructure(
            agents=best_episode.agents_involved,
            dependencies=best_episode.execution_trace["dependencies"],
            parallel_groups=best_episode.execution_trace["parallel_groups"],
            estimated_duration=best_episode.execution_time
        )

        return dag_structure
```

---

## 4. 实现路线图

### Phase 1: 记忆系统核心 (Week 1-2)

**后端**:
- [ ] 创建 `backend/src/core/memory/` 模块
- [ ] 实现 `SemanticMemoryService` (扩展现有知识库)
- [ ] 重构 `EpisodicMemoryService` (增加字段)
- [ ] 实现 `WorkingMemoryService` (Redis 层)
- [ ] 实现 `MultiTierMemoryRetrieval` (跨层检索)
- [ ] 实现记忆迁移 pipeline (工作 → 情景 → 语义)

**数据库**:
```sql
-- 语义记忆表
CREATE TABLE semantic_memories (
    id UUID PRIMARY KEY,
    knowledge_type VARCHAR(50),
    content TEXT,
    embedding VECTOR(1536),
    related_concepts JSONB,
    confidence_score FLOAT,
    access_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 情景记忆增强表
ALTER TABLE episodic_memories
ADD COLUMN agents_involved JSONB,
ADD COLUMN execution_trace JSONB,
ADD COLUMN reasoning_chain JSONB,
ADD COLUMN success_metrics JSONB,
ADD COLUMN is_successful BOOLEAN,
ADD COLUMN learned_patterns JSONB;
```

**前端**:
- [ ] 创建记忆可视化组件 `MemoryVisualization.tsx`
- [ ] 在对话中显示"使用历史案例"标记
- [ ] 添加记忆反馈界面 (评分、评论)

---

### Phase 2: 进化能力实现 (Week 3-4)

**后端**:
- [ ] 实现 `FeedbackPipeline` (反馈处理)
- [ ] 实现 `ExperienceExtractor` (经验提取)
- [ ] 实现 `PatternStore` (模式存储)
- [ ] 实现 `PolicyOptimizer` (策略优化)
- [ ] 集成到 `workforce.py` (动态 Agent 选择)

**核心逻辑**:
```python
# workforce.py 增强
class LegalWorkforce:
    async def process_task(self, task_description: str, ...):
        # 1️⃣ 使用策略优化器选择 Agent
        agents = await self.policy_optimizer.optimize_agent_selection(
            task_description, task_type
        )

        # 2️⃣ 使用策略优化器构建 DAG
        dag = await self.policy_optimizer.optimize_dag_structure(
            task_description, task_type, agents
        )

        # 3️⃣ 执行任务
        result = await self._execute_dag(dag, context)

        # 4️⃣ 记录执行轨迹
        await self.working_memory.set_execution_trace(result.trace)

        return result
```

---

### Phase 3: 监控与分析 (Week 5)

**Dashboard**:
- [ ] 记忆系统统计 (存储量、访问频率)
- [ ] 进化指标 (模式数量、优化效果)
- [ ] Agent 性能对比
- [ ] 用户反馈趋势

**可视化**:
```
┌────────────────────────────────────────────┐
│  记忆系统概览                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ 语义记忆  │  │ 情景记忆  │  │ 工作记忆  │ │
│  │ 12,450   │  │ 3,280    │  │ 156      │ │
│  │ 条       │  │ 案例     │  │ 会话     │ │
│  └──────────┘  └──────────┘  └──────────┘ │
│                                            │
│  进化指标                                  │
│  • 已提取模式: 847                        │
│  • Agent 优化: +23% 效率提升               │
│  • 用户满意度: 4.2/5.0 ↑ 0.3              │
└────────────────────────────────────────────┘
```

---

## 5. 技术栈总结

| 层级 | 技术 | 用途 |
|------|------|------|
| **语义记忆** | Qdrant + PostgreSQL | 向量搜索 + 知识图谱 |
| **情景记忆** | Qdrant + PostgreSQL | 案例检索 + 结构化存储 |
| **工作记忆** | Redis | 会话状态 + 缓存 |
| **事件总线** | Redis Pub/Sub | 异步通信 |
| **任务编排** | Camel AI | DAG 执行 |
| **向量嵌入** | OpenAI Embeddings / DeepSeek | 语义理解 |
| **监控** | Prometheus + Grafana | 性能监控 |

---

## 6. 关键指标

### 记忆系统性能指标
- **检索延迟**: < 100ms (工作记忆), < 500ms (情景记忆), < 2s (语义记忆)
- **检索准确率**: > 0.85 (相似度分数)
- **存储效率**: 支持百万级记忆条目

### 进化系统效果指标
- **模式提取率**: > 70% (成功案例中提取有效模式)
- **优化效果**: Agent 选择准确率提升 > 20%
- **用户满意度**: 平均评分提升 > 0.3 分

---

## 7. 风险与挑战

### 7.1 技术风险
- **记忆一致性**: 多层记忆之间的数据一致性
- **隐私保护**: 情景记忆可能包含敏感信息
- **计算成本**: 大规模向量检索的性能

### 7.2 缓解措施
- 实现记忆版本控制和冲突解决机制
- 自动脱敏和匿名化处理
- 分片索引和缓存策略

---

## 8. 下一步行动

1. **立即开始**: 创建 `backend/src/core/memory/` 目录结构
2. **第一周**: 实现工作记忆层 (Redis) 和情景记忆增强
3. **第二周**: 实现跨层检索 pipeline
4. **第三周**: 实现进化能力 (反馈 → 经验 → 策略)
5. **第四周**: 集成测试和性能优化
