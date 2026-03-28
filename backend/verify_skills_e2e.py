import requests
import json
import time
import sys

BASE_URL = "http://localhost:8002/api/v1"

def wait_for_backend():
    print("Waiting for backend to start...")
    for i in range(30):
        try:
            response = requests.get(f"http://localhost:8002/health")
            if response.status_code == 200:
                print("Backend is ready!")
                return True
        except:
            pass
        time.sleep(1)
    print("Backend failed to start.")
    return False

def test_labor_law_skill():
    print("\n--- Testing Labor Law Skill ---")
    query = "公司想辞退一名试用期员工，因为他不符合录用条件，需要赔偿吗？"
    
    payload = {
        "content": query
    }
    
    try:
        # Use simple chat endpoint which routes to Coordinator -> Legal Advisor
        response = requests.post(f"{BASE_URL}/chat/", json=payload)
        if response.status_code == 200:
            data = response.json()
            # Response format is UnifiedResponse, data is inside "data" -> "content"
            content = data.get("data", {}).get("content", "")
            try:
                print(f"Response: {content[:200]}...")
            except:
                print(f"Response: [Content with encoding issues, length: {len(content)}]")
            
            # Check for keywords from the skill file
            keywords = ["试用期", "不符合录用条件", "无经济补偿", "21"] # 21 might appear in citation but let's look for "无需支付" or "第39条"
        
            found = False
            if "无需支付" in content or "不需要赔偿" in content or "第39条" in content:
                found = True
                print("SUCCESS: Labor law skill logic detected (no compensation for probation unfitness).")
            else:
                print("WARNING: Specific skill keywords not strictly found, but response might still be valid.")
                
            return found
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_ip_infringement_skill():
    print("\n--- Testing IP Infringement Skill ---")
    query = "有人抄袭了我的文章，怎么判定是否侵权？"
    
    payload = {
        "content": query
    }
    
    try:
        response = requests.post(f"{BASE_URL}/chat/", json=payload)
        if response.status_code == 200:
            data = response.json()
            content = data.get("data", {}).get("content", "")
            print(f"Response: {content[:200]}...")
            
            # Check for keywords from the skill file
            if "接触" in content and "实质性相似" in content:
                print("SUCCESS: IP infringement skill detected (Access + Substantial Similarity).")
                return True
            else:
                print("WARNING: 'Contact + Substantial Similarity' principle not explicitly mentioned.")
                return False
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    if wait_for_backend():
        # Give it a few more seconds for agents to init
        time.sleep(5) 
        
        test_labor_law_skill()
        test_ip_infringement_skill()
