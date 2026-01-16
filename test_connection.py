#!/usr/bin/env python3
"""
Tennis Rules RAG - 연결 테스트 스크립트
ETL 실행 전 Supabase 및 Gemini API 연결을 테스트합니다.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def test_env_variables():
    """환경 변수 확인"""
    print("=" * 50)
    print("1. 환경 변수 확인")
    print("=" * 50)

    required_vars = {
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_SERVICE_KEY": os.getenv("SUPABASE_SERVICE_KEY"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY")
    }

    all_valid = True
    for key, value in required_vars.items():
        if not value:
            print(f"❌ {key}: 누락됨")
            all_valid = False
        elif "your-" in value.lower() or "placeholder" in value.lower():
            print(f"❌ {key}: 플레이스홀더 값입니다. 실제 값으로 교체 필요")
            all_valid = False
        else:
            masked = value[:10] + "..." + value[-5:] if len(value) > 15 else value
            print(f"✅ {key}: {masked}")

    return all_valid

def test_supabase_connection():
    """Supabase 연결 테스트"""
    print("\n" + "=" * 50)
    print("2. Supabase 연결 테스트")
    print("=" * 50)

    try:
        from supabase import create_client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")

        client = create_client(url, key)

        # 테이블 존재 확인
        result = client.table("tennis_rules").select("id").limit(1).execute()
        print(f"✅ Supabase 연결 성공")
        print(f"   - tennis_rules 테이블: 존재함")
        print(f"   - 현재 레코드 수 확인 중...")

        count_result = client.table("tennis_rules").select("id", count="exact").execute()
        count = count_result.count if hasattr(count_result, 'count') else 0
        print(f"   - 레코드 수: {count}개")

        return True

    except ImportError:
        print("❌ supabase-py 패키지가 설치되지 않았습니다.")
        print("   pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        return False

def test_gemini_api():
    """Gemini API 연결 테스트"""
    print("\n" + "=" * 50)
    print("3. Gemini API 테스트")
    print("=" * 50)

    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)

        # 간단한 임베딩 생성 테스트
        test_text = "테니스 규칙 테스트"
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=test_text,
            task_type="retrieval_document",
            output_dimensionality=768
        )

        embedding = None
        if hasattr(result, 'embedding'):
            embedding = getattr(result, 'embedding')
        elif isinstance(result, dict) and 'embedding' in result:
            embedding = result['embedding']

        if embedding and len(embedding) == 768:
            print(f"✅ Gemini API 연결 성공")
            print(f"   - 임베딩 생성 테스트: 성공")
            print(f"   - 벡터 차원: {len(embedding)}차원")
            return True
        else:
            print(f"❌ 임베딩 형식이 예상과 다릅니다: {type(result)}")
            return False

    except ImportError:
        print("❌ google-generativeai 패키지가 설치되지 않았습니다.")
        print("   pip install google-generativeai")
        return False
    except Exception as e:
        print(f"❌ Gemini API 호출 실패: {e}")
        print("   - API 키가 유효한지 확인하세요")
        print("   - API 사용이 활성화되어 있는지 확인하세요")
        return False

def test_pdf_file():
    """PDF 파일 존재 확인"""
    print("\n" + "=" * 50)
    print("4. PDF 파일 확인")
    print("=" * 50)

    pdf_files = [
        "./테니스규정집(2020.11.20 개정판).pdf"
    ]

    found = []
    missing = []

    for pdf in pdf_files:
        if os.path.exists(pdf):
            size_mb = os.path.getsize(pdf) / (1024 * 1024)
            print(f"✅ {pdf} ({size_mb:.2f} MB)")
            found.append(pdf)
        else:
            print(f"❌ {pdf} - 파일이 없습니다")
            missing.append(pdf)

    if missing:
        print("\n💡 원격 PDF는 ETL 실행 시 자동 다운로드됩니다.")

    return len(found) > 0

def main():
    """전체 테스트 실행"""
    print("\n" + "🎾" * 25)
    print("   Tennis Rules RAG - 연결 테스트")
    print("🎾" * 25 + "\n")

    results = []

    results.append(("환경 변수", test_env_variables()))
    results.append(("Supabase", test_supabase_connection()))
    results.append(("Gemini API", test_gemini_api()))
    results.append(("PDF 파일", test_pdf_file()))

    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "-" * 50)
    if all_passed:
        print("🎉 모든 테스트를 통과했습니다!")
        print("이제 ETL 스크립트를 실행할 수 있습니다:")
        print("  python etl_tennis_supabase.py")
    else:
        print("⚠️  일부 테스트가 실패했습니다.")
        print("위의 오류 메시지를 확인하고 문제를 해결하세요.")
        sys.exit(1)

if __name__ == "__main__":
    main()
