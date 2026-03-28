import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.workforce import get_workforce
from src.services.episodic_memory_service import EpisodicMemoryService
from src.services.skill_service import SkillService

async def test_comprehensive_flow():
    print("[START] 开始全功能流程测试 (Comprehensive System Test)...")
    
    # Initialize Services
    workforce = get_workforce()
    memory_service = EpisodicMemoryService()
    skill_service = SkillService()
    await memory_service.ensure_initialized()
    
    print("[OK] 服务初始化完成")

    # Test Case Data
    case_description = """
    我司（A科技）作为供应商，向B国企提供了一批服务器设备，合同总金额500万。
    合同约定验收后30天内付款。现在已经验收超过3个月，对方仍未付款。
    听说B国企最近有一些公开招投标项目中标。
    请帮我分析：
    1. 对方是否有支付能力？能否查到财产线索？
    2. 我现在该怎么办？起诉还是发函？
    3. 帮我起草一份催款律师函。
    """
    
    session_id = str(uuid.uuid4())
    print(f"\n[INPUT] 模拟用户输入 (Session: {session_id}):")
    print("-" * 50)
    print(case_description.strip())
    print("-" * 50)

    # 1. 技能匹配测试
    print("\n[TEST 1] 动态技能匹配 (Skill Matching)")
    matched_skills = skill_service.match_skills(case_description)
    print(f"匹配到的技能: {[s.name for s in matched_skills]}")
    
    has_asset_tracing = any(s.name == 'asset-tracing' for s in matched_skills)
    if has_asset_tracing:
        print("[PASS] 成功匹配 'asset-tracing' 技能")
    else:
        print("[FAIL] 未匹配到 'asset-tracing' 技能")

    # 2. 任务执行与意图识别
    print("\n[TEST 2] 任务执行与意图路由 (Execution & Intent Routing)")
    start_time = datetime.now()
    
    try:
        response = await workforce.process_task(case_description, session_id=session_id)
        
        duration = (datetime.now() - start_time).total_seconds()
        print(f"[INFO] 任务耗时: {duration:.2f}秒")
        print("\n[RESPONSE] Agent 响应摘要:")
        final_result = response.get('final_result', '')
        print(final_result[:200] + "..." if len(final_result) > 200 else final_result)
        
        # Verify Memory ID
        memory_id = response.get('memory_id')
        if memory_id:
            print(f"[PASS] 成功生成情景记忆 ID: {memory_id}")
        else:
            print("[FAIL] 未生成 Memory ID")

    except Exception as e:
        print(f"[ERROR] 任务执行失败: {str(e)}")
        # Continue to allow other tests if possible, but usually execution stops here
        # But we want to test memory if response exists. If exception, we can't.
        return

    # 3. 记忆反馈测试
    if memory_id:
        print("\n[TEST 3] 反馈闭环 (Feedback Loop)")
        try:
            await memory_service.update_feedback(memory_id, rating=5, comment="分析非常透彻，资产线索很有用！")
            print("[PASS] 反馈提交成功 (Rating: 5)")
            
            # Verify retrieval
            print("   验证记忆检索...")
            similar = await memory_service.retrieve_similar_cases("拖欠货款 资产线索")
            found = any(m['id'] == memory_id for m in similar)
            if found:
                print(f"[PASS] 成功检索到刚刚存储的记忆 (ID: {memory_id})")
            else:
                print("[WARN] 警告: 检索未立即返回新记忆 (可能是索引延迟)")
        except Exception as e:
            print(f"[FAIL] 反馈测试失败: {str(e)}")

    # 4. 简报生成测试 (模拟 API 调用)
    print("\n[TEST 4] 案件简报生成 (Legal Briefing Generation)")
    briefing_prompt = f"""
    请基于上述分析结果，生成一份【律师交接简报】。
    包含：案情摘要、资产线索关键点、下一步行动建议。
    上下文: {response.get('final_result', '')}
    """
    
    try:
        briefing = await workforce.chat(briefing_prompt, agent_name="document_drafter")
        print("\n[BRIEFING] 生成的简报内容:")
        print("-" * 30)
        print(briefing[:300] + "...")
        print("-" * 30)
        print("[PASS] 简报生成成功")
    except Exception as e:
        print(f"[FAIL] 简报生成失败: {str(e)}")

    print("\n[DONE] 全功能测试完成！")

if __name__ == "__main__":
    asyncio.run(test_comprehensive_flow())
