#!/bin/bash

# Tennis Rules RAG - Quick Start Script
# 이 스크립트는 처음 설정을 도와줍니다.

set -e

echo "========================================="
echo "🎾 Tennis Rules RAG - Quick Start"
echo "========================================="
echo ""

# 1. Python 버전 확인
echo "1. Python 버전 확인..."
python3 --version || { echo "❌ Python 3이 설치되어 있지 않습니다."; exit 1; }
echo "✅ Python 확인 완료"
echo ""

# 2. 가상환경 생성
echo "2. Python 가상환경 생성..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 가상환경 생성 완료"
else
    echo "✅ 가상환경이 이미 존재합니다"
fi
echo ""

# 3. 가상환경 활성화
echo "3. 가상환경 활성화..."
source venv/bin/activate || . venv/Scripts/activate
echo "✅ 가상환경 활성화 완료"
echo ""

# 4. 패키지 설치
echo "4. Python 패키지 설치..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ 패키지 설치 완료"
echo ""

# 5. .env 파일 확인
echo "5. 환경 변수 확인..."
if [ ! -f ".env" ]; then
    echo "❌ .env 파일이 없습니다."
    echo "   .env 파일을 생성하고 API 키를 입력하세요."
    exit 1
fi
echo "✅ .env 파일 존재"
echo ""

# 6. 연결 테스트
echo "6. Supabase 및 Gemini API 연결 테스트..."
python test_connection.py

# 7. 다음 단계 안내
echo ""
echo "========================================="
echo "✨ 설정이 완료되었습니다!"
echo "========================================="
echo ""
echo "다음 단계:"
echo "1. Supabase에서 supabase_setup.sql 실행"
echo "2. python etl_tennis_supabase.py 실행하여 데이터 적재"
echo "3. supabase functions deploy tennis-rag-query로 Edge Function 배포"
echo "4. python -m http.server 8000으로 웹 UI 실행"
echo ""
echo "자세한 내용은 SETUP_GUIDE.md를 참고하세요."
echo ""
