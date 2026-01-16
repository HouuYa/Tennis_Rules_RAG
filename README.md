# 🎾 Tennis Rules RAG System

ITF 및 KTA 테니스 규칙집 기반 질의응답 시스템 (RAG - Retrieval Augmented Generation)

## ✨ 주요 기능

- 📚 **다국어 규칙 지원**: ITF(영문), KTA(한글) 규칙집 통합
- 🧩 **조항별 Chunking**: 규칙 조항 단위로 지능적 분할
- 🔍 **벡터 유사도 검색**: pgvector + Gemini Embeddings (768차원)
- 🤖 **AI 답변 생성**: Gemini 1.5 Flash 기반 정확한 답변
- 🔐 **사용자 API 키**: AI Coach와 동일한 Gemini API 키 재사용
- 💬 **실시간 채팅 UI**: 직관적인 웹 인터페이스

## 🏗️ 시스템 구조

```
┌─────────────────┐
│  PDF Documents  │  ITF Rules, KTA Rules
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   ETL Script    │  Python + pdfplumber
│  (One-time run) │  → Chunking → Gemini Embeddings
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Supabase     │
│   + pgvector    │  tennis_rules table
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Edge Function  │  Query → Embedding → Search
│   (Serverless)  │  → Gemini Answer
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Web UI        │  tennis_chat.html
│   (Frontend)    │  실시간 채팅 인터페이스
└─────────────────┘
```

## 🚀 빠른 시작

### 1. 저장소 클론
```bash
git clone <repository-url>
cd Tennis_Rules_RAG
```

### 2. Python 패키지 설치
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 환경 변수 설정
`.env` 파일을 편집하여 실제 API 키 입력:
```env
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SERVICE_KEY="eyJhbGc..."
GEMINI_API_KEY="AIzaSyC..."
```

### 4. Supabase 설정
1. Supabase 대시보드 → SQL Editor
2. `supabase_setup.sql` 내용 복사 & 실행

### 5. 연결 테스트
```bash
python test_connection.py
```

### 6. ETL 실행
```bash
python etl_tennis_supabase.py
```

### 7. Edge Function 배포
```bash
supabase login
supabase link --project-ref your-project-id
supabase functions deploy tennis-rag-query
```

### 8. 프론트엔드 실행
```bash
# tennis_chat.html에서 Edge Function URL 수정
python -m http.server 8000
# http://localhost:8000/tennis_chat.html 접속
```

## 📁 파일 구조

```
Tennis_Rules_RAG/
├── etl_tennis_supabase.py      # ETL 메인 스크립트
├── test_connection.py           # 연결 테스트 스크립트
├── requirements.txt             # Python 패키지
├── .env                         # 환경 변수 (git 제외)
├── supabase_setup.sql           # Supabase 초기화 SQL
├── tennis_chat.html             # 채팅 웹 UI
├── SETUP_GUIDE.md               # 상세 설정 가이드
├── README.md                    # 이 파일
└── supabase/
    ├── config.toml              # Supabase 로컬 설정
    └── functions/
        └── tennis-rag-query/
            └── index.ts         # Edge Function 코드
```

## 🔧 사용 방법

### ETL 스크립트 옵션
```bash
# 전체 실행 (로컬 + 원격 PDF)
python etl_tennis_supabase.py

# 드라이 런 (DB 쓰기 없이 테스트)
DRY_RUN=1 python etl_tennis_supabase.py

# 임베딩 생성 스킵 (청크 분할만 테스트)
SKIP_EMBEDDING=1 python etl_tennis_supabase.py

# 원격 파일 다운로드 스킵
SKIP_REMOTE=1 python etl_tennis_supabase.py
```

### Edge Function API 사용
```bash
curl -X POST \
  https://your-project.supabase.co/functions/v1/tennis-rag-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "서브 폴트는 어떤 경우인가요?",
    "gemini_api_key": "YOUR_API_KEY",
    "match_count": 5,
    "match_threshold": 0.3
  }'
```

### 웹 UI 사용
1. Gemini API Key 입력 (AI Coach와 동일)
2. 질문 입력:
   - "서브 폴트는 어떤 경우인가요?"
   - "타이브레이크 규칙을 알려주세요"
   - "Let이란 무엇인가요?"
3. AI 답변 및 참고 규칙 확인

## 📊 데이터베이스 구조

### tennis_rules 테이블
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | BIGSERIAL | Primary Key |
| source_file | TEXT | 출처 파일명 |
| rule_id | TEXT | 규칙 조항 ID |
| content | TEXT | 조항 내용 (검색용) |
| metadata | JSONB | 메타데이터 |
| embedding | VECTOR(768) | Gemini 임베딩 벡터 |
| created_at | TIMESTAMPTZ | 생성 시간 |

### 주요 함수
```sql
-- 벡터 유사도 검색
match_tennis_rules(
  query_embedding VECTOR(768),
  match_threshold FLOAT DEFAULT 0.3,
  match_count INT DEFAULT 10
)
```

## 🎯 성능 최적화

### 인덱스
- HNSW 인덱스: `embedding` 컬럼 (고속 벡터 검색)
- B-tree 인덱스: `rule_id`, `source_file` (필터링 검색)

### 배치 처리
- ETL: 10개씩 배치로 임베딩 생성 및 업로드
- Rate limiting: 임베딩 요청 간 0.2초 대기

### 벡터 정규화
- L2 정규화 적용 (코사인 유사도 최적화)
- 내적(inner product) 기반 검색 사용

## 🐛 문제 해결

### 자주 발생하는 오류

#### 1. "GEMINI_API_KEY가 비어있거나 플레이스홀더로 보입니다"
→ `.env` 파일에서 실제 API 키로 교체

#### 2. "supabase client 초기화 실패"
→ `pip install supabase --upgrade`

#### 3. CORS 오류
→ Edge Function의 `corsHeaders` 확인

#### 4. 검색 결과 없음
→ `match_threshold`를 0.1로 낮춤

자세한 내용은 [SETUP_GUIDE.md](SETUP_GUIDE.md) 참조

## 📚 기술 스택

- **Backend**: Python 3.8+
- **Vector DB**: Supabase + pgvector
- **Embeddings**: Google Gemini Embedding API (768d)
- **LLM**: Gemini 1.5 Flash
- **PDF Processing**: pdfplumber
- **Serverless**: Supabase Edge Functions (Deno)
- **Frontend**: Vanilla JavaScript + HTML/CSS

## 🔐 보안

- ✅ RLS (Row Level Security) 설정
- ✅ Service Role Key는 서버에서만 사용
- ✅ 사용자 API 키는 클라이언트에서만 처리
- ⚠️ `.env` 파일은 Git에 절대 커밋 금지
- ⚠️ 프로덕션 환경에서는 HTTPS 필수

## 📈 로드맵

- [ ] 멀티턴 대화 지원
- [ ] 채팅 히스토리 저장
- [ ] 다국어 자동 감지
- [ ] 이미지/다이어그램 표시
- [ ] 모바일 앱 개발
- [ ] 검색 품질 평가 시스템

## 🤝 기여

이슈와 PR을 환영합니다!

## 📄 라이선스

MIT License

## 📧 문의

프로젝트 관련 문의는 GitHub Issues에 등록해주세요.

---

Made with ❤️ for Tennis Players
