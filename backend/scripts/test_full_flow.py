import asyncio
import httpx
import sys
import os
import json

# 配置
API_BASE_URL = "http://localhost:8001/api/v1"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

async def run_test():
    print(f"开始全流程测试 - 连接至 {API_BASE_URL}")
    
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        # 1. 登录
        print("\n[1/5] 登录管理员账号...")
        try:
            response = await client.post("/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            if response.status_code != 200:
                print(f"[X] 登录失败: {response.text}")
                return
            
            token_data = response.json()
            access_token = token_data["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            print(f"[OK] 登录成功! Token获取完成 (User: {token_data['user']['name']})")
        except httpx.ConnectError:
            print("[X] 连接失败: 请确保后端服务已启动 (localhost:8001)")
            return

        # 2. 创建案件
        print("\n[2/5] 创建测试案件...")
        case_data = {
            "title": "自动化测试案件 - 合同违约",
            "case_type": "contract",
            "description": "这是一个由自动化脚本创建的测试案件，用于验证系统流程。",
            "priority": "medium",
            "deadline": "2024-12-31T00:00:00"
        }
        response = await client.post("/cases/", json=case_data, headers=headers)
        if response.status_code not in [200, 201]:
            print(f"[X] 创建案件失败: {response.text}")
            return
        
        case_data_resp = response.json()
        # Handle UnifiedResponse wrapper if present
        if "data" in case_data_resp:
            case = case_data_resp["data"]
        else:
            case = case_data_resp
            
        case_id = case["id"]
        print(f"[OK] 案件创建成功! ID: {case_id}")

        # 3. 上传文档 (模拟)
        print("\n[3/5] 上传案件文档...")
        # 创建一个临时文件
        files = {'file': ('test_contract.txt', b'This is a test contract content for AI analysis.', 'text/plain')}
        data = {'case_id': case_id, 'doc_type': 'contract', 'description': '测试合同文件'}
        
        response = await client.post("/documents/", files=files, data=data, headers=headers)
        if response.status_code not in [200, 201]:
            print(f"[X] 上传文档失败: {response.text}")
        else:
            doc_resp = response.json()
            if "data" in doc_resp:
                doc = doc_resp["data"]
            else:
                doc = doc_resp
            print(f"[OK] 文档上传成功! ID: {doc['id']}")

        # 4. 发起对话 (WebSocket 测试较复杂，这里使用 HTTP 消息接口)
        print("\n[4/5] 测试 AI 对话 (通过 HTTP)...")
        chat_msg = {
            "content": "请分析这个案件的风险点",
            "case_id": case_id
        }
        
        # 注意: 如果 /chat/ 是流式的，可能需要处理流
        # 这里假设有一个非流式或者我们只看连接是否成功
        # 尝试使用 stream 接口但作为普通请求
        try:
            async with client.stream("POST", "/chat/stream", json=chat_msg, headers=headers) as stream_response:
                if stream_response.status_code != 200:
                    print(f"[X] 对话请求失败: {stream_response.status_code}")
                else:
                    print("[OK] 对话请求连接成功，接收流式响应...")
                    full_response = ""
                    async for chunk in stream_response.aiter_text():
                        # 简单打印部分响应以验证
                        if "data: " in chunk:
                            print(".", end="", flush=True)
                            full_response += chunk
                    print("\n[OK] 对话响应接收完成")
        except Exception as e:
            print(f"[!] 对话测试遇到问题 (可能是因为 LLM 未配置或超时): {e}")

        # 5. 验证知识库/Dashboard 数据
        print("\n[5/5] 验证统计数据...")
        response = await client.get("/cases/statistics/overview", headers=headers)
        if response.status_code == 200:
            stats_resp = response.json()
            if "data" in stats_resp:
                stats = stats_resp["data"]
            else:
                stats = stats_resp
            print(f"[OK] 统计数据获取成功: 当前共有 {stats['total']} 个案件")
        else:
            print(f"[X] 获取统计失败: {response.text}")

    print("\n========================================")
    print("全流程测试完成!")
    print("========================================")

if __name__ == "__main__":
    # 需要安装 httpx: pip install httpx
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        pass
