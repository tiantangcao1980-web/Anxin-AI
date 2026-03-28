import asyncio
import sys
import os
from loguru import logger

# 添加 src 到路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.agents.workforce import get_workforce
from src.services.episodic_memory_service import episodic_memory

# Mock LLM 响应，避免真实调用 API (如果环境变量没配好的话)
# 在真实环境中，请确保 .env 中有 LLM_API_KEY
from unittest.mock import MagicMock

async def demo_evolution():
    print("\n" + "="*50)
    print("🚀 开始 AI 法务系统「自我进化」演示")
    print("="*50 + "\n")

    workforce = get_workforce()
    
    # ------------------------------------------------------------
    # 场景 1: 第一次遇到复杂任务
    # ------------------------------------------------------------
    task1 = "请帮我审查这份《软件开发外包合同》，重点关注知识产权归属条款，如果是乙方开发的代码，版权属于谁？"
    print(f"📝 [Task 1] 用户提交任务: {task1[:30]}...")
    
    # 执行任务
    # 注意：这里会真实调用 LLM 进行意图识别和规划
    # 如果没有配置 API Key，可能会报错，建议确保环境正常
    try:
        result1 = await workforce.process_task(task1)
    except Exception as e:
        print(f"❌ 任务执行失败 (可能是 API Key 问题): {e}")
        return

    memory_id = result1.get("memory_id")
    print(f"✅ [Task 1] 执行完成!")
    print(f"   - 意图识别: {result1['analysis'].get('intent', 'N/A')}")
    print(f"   - 规划步骤: {len(result1['analysis'].get('plan', []))}")
    print(f"   - 记忆 ID: {memory_id}")
    
    if not memory_id:
        print("❌ 未生成记忆 ID，后续无法演示反馈。")
        return

    # ------------------------------------------------------------
    # 场景 2: 人类反馈 (强化学习信号)
    # ------------------------------------------------------------
    print(f"\n👍 [Feedback] 用户对 Task 1 给出了 5 星好评！")
    await episodic_memory.update_feedback(memory_id, rating=5, comment="规划得很清晰，特别是知识产权部分的审查")
    print(f"   - 系统已更新记忆权重，标记为「成功经验」")
    
    # 稍作等待，确保向量库刷新（如果是异步写入）
    await asyncio.sleep(1)

    # ------------------------------------------------------------
    # 场景 3: 再次遇到类似任务 (触发记忆检索)
    # ------------------------------------------------------------
    task2 = "审查一份APP开发协议，看看代码版权是不是归我所有？"
    print(f"\n📝 [Task 2] 用户提交相似任务: {task2[:30]}...")
    print("   - 正在检索历史记忆...")

    # 我们手动调用检索来看看结果
    similar_cases = await episodic_memory.retrieve_similar_cases(task2)
    
    if similar_cases:
        top_case = similar_cases[0]
        print(f"\n✨ [Evolution] 成功检索到历史经验！")
        print(f"   - 相似度: {top_case['similarity_score']:.4f}")
        print(f"   - 历史评分: {top_case['rating']} ⭐")
        print(f"   - 历史任务: {top_case['task']}")
        print(f"   - 历史结果摘要: {top_case['result_summary'][:50]}...")
        print(f"\n🧠 系统将自动复用 Task 1 的成功规划路径...")
    else:
        print(f"\n❌ 未检索到相似记忆 (可能向量库未初始化或相似度阈值过高)")

    print("\n" + "="*50)
    print("演示结束")
    print("="*50)

if __name__ == "__main__":
    # 确保日志不会刷屏
    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    
    asyncio.run(demo_evolution())
