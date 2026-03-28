import asyncio
import sys
import os
import json
from datetime import datetime
from loguru import logger

# 添加 src 到路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.database import async_session_maker
from src.services.episodic_memory_service import episodic_memory
from src.services.vector_store import vector_store

# 模拟历史案例数据
HISTORY_CASES = [
    {
        "task": "请审查这份《软件外包开发合同》，特别是知识产权归属条款。",
        "plan": [
            {"id": "t1", "agent": "contract_reviewer", "instruction": "提取合同中的IP归属条款", "depends_on": []},
            {"id": "t2", "agent": "risk_assessor", "instruction": "评估IP条款对委托方的风险", "depends_on": ["t1"]},
            {"id": "t3", "agent": "legal_advisor", "instruction": "提供修改建议", "depends_on": ["t2"]}
        ],
        "result_summary": "发现高风险：代码版权约定不明。建议增加：'乙方交付的所有代码及文档，其知识产权归甲方所有'。",
        "rating": 5
    },
    {
        "task": "调查一下'深空科技有限公司'的背景，有没有诉讼风险？",
        "plan": [
            {"id": "t1", "agent": "due_diligence", "instruction": "查询工商信息及涉诉记录", "depends_on": []},
            {"id": "t2", "agent": "risk_assessor", "instruction": "根据涉诉情况评级", "depends_on": ["t1"]}
        ],
        "result_summary": "该公司存在3起未结案的合同纠纷诉讼，风险等级：中。建议在交易前要求其提供履约担保。",
        "rating": 4
    }
]

async def seed_data():
    logger.info("开始构造测试数据...")
    
    # 1. 确保向量集合存在
    await episodic_memory.ensure_initialized()
    
    # 2. 注入情景记忆
    logger.info(f"正在注入 {len(HISTORY_CASES)} 条历史成功经验...")
    
    for case in HISTORY_CASES:
        # 模拟 process_task 的结果结构
        mock_result = {"summary": case["result_summary"]}
        mock_feedback = {"rating": case["rating"], "comment": "系统预置数据"}
        
        await episodic_memory.add_memory(
            task_description=case["task"],
            plan=case["plan"],
            final_result=mock_result,
            user_feedback=mock_feedback,
            metadata={"source": "seed_script", "is_preset": True}
        )
        
    logger.info("✅ 历史记忆注入完成！系统现在具备了初步的法务经验。")
    
    # 3. 验证检索
    test_query = "帮我看看这个外包合同的版权问题"
    results = await episodic_memory.retrieve_similar_cases(test_query)
    
    if results:
        logger.info(f"🔍 检索测试成功: 输入 '{test_query}' -> 匹配到记忆 (相似度: {results[0]['similarity_score']:.4f})")
    else:
        logger.warning("⚠️ 检索测试失败，请检查 Qdrant 服务是否正常。")

if __name__ == "__main__":
    try:
        asyncio.run(seed_data())
    except Exception as e:
        logger.error(f"数据构造失败: {e}")
