import requests
import json

try:
    response = requests.get("http://localhost:8001/api/v1/llm/providers")
    if response.status_code == 200:
        data = response.json()
        moonshot = data.get("moonshot", {})
        models = moonshot.get("models", {}).get("llm", [])
        print(f"Moonshot models: {models}")
        if "kimi-k2.5" in models:
            print("SUCCESS: kimi-k2.5 found!")
        else:
            print("FAILURE: kimi-k2.5 NOT found.")
    else:
        print(f"Error: {response.status_code}")
except Exception as e:
    print(f"Exception: {e}")
