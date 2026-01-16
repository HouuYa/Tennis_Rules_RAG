#!/usr/bin/env python3
"""
Tennis Rules RAG - 데이터 검증 스크립트
ETL 실행 후 Supabase에 저장된 데이터를 검증합니다.
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def main():
    print("=" * 50)
    print("Tennis Rules RAG - 데이터 검증")
    print("=" * 50 + "\n")

    # Supabase 연결
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("❌ .env 파일에 SUPABASE_URL 또는 SUPABASE_SERVICE_KEY가 없습니다.")
        return

    client = create_client(url, key)

    # 1. 전체 레코드 수
    print("1. 전체 레코드 수")
    result = client.table("tennis_rules").select("id", count="exact").execute()
    total_count = result.count if hasattr(result, 'count') else len(result.data)
    print(f"   총 {total_count}개의 레코드\n")

    # 2. 파일별 분포
    print("2. 파일별 레코드 분포")
    result = client.table("tennis_rules") \
        .select("source_file") \
        .execute()

    from collections import Counter
    file_counts = Counter([r['source_file'] for r in result.data])
    for file, count in file_counts.items():
        print(f"   - {file}: {count}개")
    print()

    # 3. 샘플 데이터
    print("3. 샘플 데이터 (최신 5개)")
    result = client.table("tennis_rules") \
        .select("id, source_file, rule_id, content") \
        .order("created_at", desc=True) \
        .limit(5) \
        .execute()

    for r in result.data:
        print(f"\n   ID: {r['id']}")
        print(f"   출처: {r['source_file']}")
        print(f"   조항: {r['rule_id']}")
        print(f"   내용: {r['content'][:100]}...")

    # 4. 임베딩 벡터 확인
    print("\n\n4. 임베딩 벡터 확인")
    result = client.rpc("exec_sql", {
        "sql": "SELECT id, rule_id, vector_dims(embedding) as dim FROM tennis_rules LIMIT 5"
    }).execute()

    # 대체 쿼리 (RPC 실패 시)
    result = client.table("tennis_rules") \
        .select("id, rule_id, embedding") \
        .limit(3) \
        .execute()

    for r in result.data:
        emb_len = len(r.get('embedding', [])) if r.get('embedding') else 0
        status = "✅" if emb_len == 768 else "❌"
        print(f"   {status} ID {r['id']}: {r['rule_id']} - 벡터 차원: {emb_len}")

    print("\n" + "=" * 50)
    print("검증 완료!")
    print("=" * 50)

if __name__ == "__main__":
    main()
