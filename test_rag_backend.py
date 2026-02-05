import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GEMINI_API_KEY")
url = "https://ctzcgrwjsrvoxjycwtya.supabase.co/functions/v1/tennis-rag-query"

headers = {
    "Content-Type": "application/json"
}
data = {
    "question": "서브 폴트는 무엇인가요?",
    "match_count": 3,
    "gemini_api_key": key
}

print(f"Testing RAG Backend at {url}...")
try:
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        print("\n" + "="*50)
        print(f"질문: {result.get('question')}")
        print("="*50)
        
        print("\n[찾은 참고 자료]")
        sources = result.get('sources', [])
        for i, src in enumerate(sources):
            print(f"- [{i+1}] {src.get('rule_id')} (유사도: {src.get('similarity', 0):.3f})")
            content_preview = src.get('content', '').replace('\n', ' ')[:100]
            print(f"  내용: {content_preview}...")
            
        print("\n" + "="*50)
        print("[AI 답변]")
        print("-" * 50)
        print(result.get('answer'))
        print("="*50)
    else:
        print(f"Error {response.status_code}: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
