# 🎾 Tennis Rules RAG System

ITF 및 KTA 테니스 규칙집 기반 질의응답 시스템 (RAG - Retrieval Augmented Generation)

> **⚡ 빠른 참조**
> - 💻 **처음 설정**: [실행 방법 (상세 가이드)](#-실행-방법-상세-가이드) 참조
> - 📖 **더 자세한 설명**: [SETUP_GUIDE.md](SETUP_GUIDE.md) 참조
> - 🐛 **문제 발생**: [문제가 발생했나요?](#-문제가-발생했나요) 참조
> - ⏱️ **예상 소요 시간**: 초기 설정 약 30분 (API 키 발급 포함)

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

## 🚀 실행 방법 (상세 가이드)

> 💡 **처음 설정하시나요?** 이 가이드를 순서대로 따라하시면 됩니다!

### 📋 사전 준비 (필수)

시작하기 전에 다음 항목들이 준비되어 있어야 합니다:

#### ✅ 체크리스트
- [ ] Python 3.8 이상 설치됨
- [ ] Git 설치됨
- [ ] Supabase 계정 생성 (https://supabase.com - 무료)
- [ ] Google Cloud 계정 (Gemini API용 - 무료 할당량 제공)
- [ ] 텍스트 에디터 (VS Code, Notepad++ 등)

---

### 단계 1️⃣: 저장소 다운로드

```bash
# Git으로 프로젝트 다운로드
git clone https://github.com/HouuYa/Tennis_Rules_RAG.git
cd Tennis_Rules_RAG
```

**또는** ZIP 파일로 다운로드:
1. GitHub 페이지에서 `Code` → `Download ZIP` 클릭
2. 압축 해제 후 터미널/명령 프롬프트에서 해당 폴더로 이동

---

### 단계 2️⃣: Python 가상환경 설정

#### 🪟 Windows 사용자:
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
venv\Scripts\activate

# 프롬프트에 (venv)가 표시되면 성공!
```

#### 🍎 Mac / 🐧 Linux 사용자:
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 프롬프트에 (venv)가 표시되면 성공!
```

#### 패키지 설치:
```bash
# 필요한 Python 패키지 설치 (약 1-2분 소요)
pip install -r requirements.txt

# 설치 완료 메시지가 나오면 성공!
```

**예상 출력:**
```
Successfully installed supabase-1.0.0 google-generativeai-0.3.0 ...
```

---

### 단계 3️⃣: API 키 발급 및 설정

#### 3-1. Gemini API 키 발급

1. **Google AI Studio 접속**: https://makersuite.google.com/app/apikey
2. **"Create API Key"** 버튼 클릭
3. 프로젝트 선택 또는 새로 만들기
4. 생성된 API 키 복사 (예: `AIzaSyC...`)
   - ⚠️ 이 키는 다시 볼 수 없으니 안전한 곳에 보관하세요!

#### 3-2. Supabase 프로젝트 생성 및 키 확인

1. **Supabase 로그인**: https://supabase.com
2. **"New Project"** 클릭
3. 프로젝트 정보 입력:
   - Name: `tennis-rules-rag` (자유)
   - Database Password: 안전한 비밀번호 (기억하세요!)
   - Region: `Northeast Asia (Seoul)` 또는 가까운 지역
4. **Create new project** 클릭 (약 2-3분 대기)
5. 프로젝트 대시보드에서 **Settings** → **API** 메뉴로 이동
6. 다음 정보 복사:
   - **Project URL**: `https://xxxxxx.supabase.co`
   - **`service_role` key** (secret): `eyJhbGc...` (매우 긴 문자열)
   - ⚠️ `anon public` 키가 아닌 **`service_role`** 키를 사용해야 합니다!

#### 3-3. .env 파일 수정

1. 프로젝트 폴더에서 `.env` 파일을 텍스트 에디터로 열기
2. 다음과 같이 수정:

```env
# 위에서 복사한 Supabase URL
SUPABASE_URL="https://xxxxxx.supabase.co"

# 위에서 복사한 service_role secret key
SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInoooooooooo.ey..."

# 위에서 발급받은 Gemini API Key
GEMINI_API_KEY="AIzaSyC..."
```

3. 저장 후 닫기

**⚠️ 중요**:
- `"your-google-gemini-api-key"` 같은 플레이스홀더를 실제 키로 **반드시 교체**하세요!
- 따옴표(`"`)는 유지하세요

---

### 단계 4️⃣: Supabase 데이터베이스 설정

#### 4-1. SQL 에디터 열기

1. Supabase 대시보드에서 **SQL Editor** 메뉴 클릭
2. **"New query"** 버튼 클릭

#### 4-2. SQL 스크립트 실행

1. 프로젝트 폴더에서 `supabase_setup.sql` 파일을 열기
2. **파일 내용 전체 복사** (Ctrl+A → Ctrl+C)
3. Supabase SQL Editor에 **붙여넣기** (Ctrl+V)
4. 우측 하단의 **"Run"** 버튼 클릭 (또는 Ctrl+Enter)

**예상 결과:**
```
Success. No rows returned
```
또는 각 명령어마다 `Success` 메시지가 표시됩니다.

**❌ 오류가 발생하면:**
- `vector extension already exists`: 정상입니다. 무시하세요.
- `relation "tennis_rules" already exists`: 정상입니다. 무시하세요.
- 다른 오류: SETUP_GUIDE.md의 "문제 해결" 섹션을 확인하세요.

---

### 단계 5️⃣: 연결 테스트 (선택사항이지만 권장)

```bash
# 환경 변수와 API 연결 확인
python test_connection.py
```

**예상 출력:**
```
==================================================
1. 환경 변수 확인
==================================================
✅ SUPABASE_URL: https://xxx...se.co
✅ SUPABASE_SERVICE_KEY: eyJhbG...nSy
✅ GEMINI_API_KEY: AIzaSy...

==================================================
2. Supabase 연결 테스트
==================================================
✅ Supabase 연결 성공
   - tennis_rules 테이블: 존재함
   - 레코드 수: 0개

==================================================
3. Gemini API 테스트
==================================================
✅ Gemini API 연결 성공
   - 임베딩 생성 테스트: 성공
   - 벡터 차원: 768차원

==================================================
4. PDF 파일 확인
==================================================
✅ ./테니스규정집(2020.11.20 개정판).pdf (1.90 MB)

==================================================
🎉 모든 테스트를 통과했습니다!
```

**❌ 실패하면:**
- API 키가 올바른지 다시 확인
- `.env` 파일 저장을 잊지 않았는지 확인

---

### 단계 6️⃣: ETL 실행 (데이터 적재)

이 단계에서 PDF에서 텍스트를 추출하고 임베딩을 생성합니다.
⏱️ **소요 시간**: 약 10-20분 (인터넷 속도에 따라 다름)

```bash
# 전체 ETL 프로세스 실행
python etl_tennis_supabase.py
```

**실행 과정:**
```
[INFO] 🔥 ETL 프로세스 시작
[INFO] 📖 텍스트 추출 중: ./테니스규정집(2020.11.20 개정판).pdf
[INFO] ✂️  Chunking 완료: 156개 조항 생성
[INFO] 🚀 Supabase 업로드 시작 (총 156개, 배치 사이즈 10)
[INFO]   - Batch 1 업로드 완료 (10건)
[INFO]   - Batch 2 업로드 완료 (10건)
...
[INFO] 📥 다운로드 시작: https://www.itftennis.com/...
[INFO] ✅ 다운로드 완료: downloads/2025-rules-of-tennis-english.pdf
...
[INFO] 🎉 모든 작업이 완료되었습니다.
```

**💡 팁:**
- 처음 테스트하려면 드라이 런 모드 사용:
  ```bash
  DRY_RUN=1 python etl_tennis_supabase.py
  ```
- 임베딩만 테스트:
  ```bash
  SKIP_REMOTE=1 python etl_tennis_supabase.py
  ```

**데이터 확인:**
1. Supabase 대시보드 → **Table Editor** 메뉴
2. `tennis_rules` 테이블 선택
3. 데이터가 표시되면 성공!

또는 스크립트로 확인:
```bash
python verify_data.py
```

---

### 단계 7️⃣: Edge Function 배포

#### 7-1. Supabase CLI 설치

**🪟 Windows (scoop 사용):**
```bash
# scoop이 없으면 먼저 설치: https://scoop.sh
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase
```

**🍎 Mac:**
```bash
brew install supabase/tap/supabase
```

**🐧 Linux:**
```bash
brew install supabase/tap/supabase
```

#### 7-2. Supabase 로그인

```bash
supabase login
```

브라우저가 열리면 **"Authorize"** 버튼 클릭
터미널에 `Finished supabase login` 메시지가 나오면 성공!

#### 7-3. 프로젝트 연결

```bash
# Supabase 대시보드 → Settings → General에서 "Reference ID" 복사
supabase link --project-ref your-project-id
```

**예:** `supabase link --project-ref liwdnhwfgksduuqrhxwe`

**성공 메시지:**
```
Linked to project "tennis-rules-rag"
```

#### 7-4. Edge Function 배포

```bash
supabase functions deploy tennis-rag-query
```

**성공 메시지:**
```
Deploying... (100%)
Deployed function tennis-rag-query v1
Function URL: https://xxxxxx.supabase.co/functions/v1/tennis-rag-query
```

**🎯 중요**: 위의 Function URL을 복사해두세요!

---

### 단계 8️⃣: 웹 UI 설정 및 실행

#### 8-1. Edge Function URL 설정

1. `tennis_chat.html` 파일을 텍스트 에디터로 열기
2. **19번째 줄** 찾기:
   ```javascript
   const EDGE_FUNCTION_URL = 'https://liwdnhwfgksduuqrhxwe.supabase.co/functions/v1/tennis-rag-query';
   ```
3. 위에서 복사한 **실제 Function URL로 교체**
4. 저장

#### 8-2. 로컬 서버 실행

**방법 1: Python 서버 (추천)**
```bash
# Python 3.x
python -m http.server 8000

# 또는 Python 2.x
python -m SimpleHTTPServer 8000
```

**방법 2: Node.js 서버**
```bash
npx http-server -p 8000
```

**성공 메시지:**
```
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

#### 8-3. 브라우저에서 접속

1. 웹 브라우저 열기 (Chrome, Firefox, Edge 등)
2. 주소창에 입력: `http://localhost:8000/tennis_chat.html`
3. 채팅 UI가 표시되면 성공! 🎉

---

### 단계 9️⃣: 챗봇 사용하기

#### 9-1. API 키 입력
1. 상단 입력창에 **Gemini API Key** 입력
   - 단계 3에서 발급받은 키
   - AI Coach와 동일한 키 사용 가능
2. 자동으로 브라우저에 저장됨 (다음번엔 자동 입력)

#### 9-2. 질문하기
입력창에 질문 입력 후 Enter 또는 "전송" 버튼 클릭:

**예시 질문:**
- "서브 폴트는 어떤 경우인가요?"
- "타이브레이크 규칙을 알려주세요"
- "풋 폴트는 무엇인가요?"
- "테니스 공의 크기는?"
- "듀스 규칙 설명해주세요"

#### 9-3. 답변 확인
- AI 답변이 표시됨
- 아래에 참고한 규칙 조항과 유사도 점수가 표시됨

---

## 🎊 축하합니다!

모든 설정이 완료되었습니다. 이제 테니스 규칙에 대해 자유롭게 질문하세요!

---

## 🆘 문제가 발생했나요?

### 빠른 체크리스트
- [ ] `.env` 파일에 실제 API 키를 입력했나요?
- [ ] 가상환경이 활성화되어 있나요? (프롬프트에 `(venv)` 표시)
- [ ] `test_connection.py`가 성공했나요?
- [ ] Supabase SQL이 성공적으로 실행되었나요?
- [ ] Edge Function URL을 `tennis_chat.html`에 올바르게 입력했나요?

### 자세한 문제 해결
👉 [SETUP_GUIDE.md](SETUP_GUIDE.md)의 "문제 해결" 섹션 참조

### 추가 도움
- GitHub Issues에 질문 올리기
- SETUP_GUIDE.md 전체 읽어보기
- CODE_REVIEW.md에서 시스템 구조 이해하기

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

## 🔧 고급 사용 방법

### ETL 스크립트 옵션

```bash
# 전체 실행 (기본값)
python etl_tennis_supabase.py

# 드라이 런 (DB 쓰기 없이 테스트만)
DRY_RUN=1 python etl_tennis_supabase.py

# 임베딩 생성 스킵 (청크 분할만 테스트)
SKIP_EMBEDDING=1 python etl_tennis_supabase.py

# 원격 파일 다운로드 스킵 (로컬 PDF만 처리)
SKIP_REMOTE=1 python etl_tennis_supabase.py

# 여러 옵션 조합
DRY_RUN=1 SKIP_REMOTE=1 python etl_tennis_supabase.py
```

### Edge Function API 직접 호출

터미널에서 API 테스트:

```bash
curl -X POST \
  https://your-project.supabase.co/functions/v1/tennis-rag-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "서브 폴트는 어떤 경우인가요?",
    "gemini_api_key": "YOUR_GEMINI_API_KEY",
    "match_count": 5,
    "match_threshold": 0.3
  }'
```

**응답 예시:**
```json
{
  "question": "서브 폴트는 어떤 경우인가요?",
  "answer": "서브 폴트는 다음과 같은 경우에 발생합니다...",
  "sources": [
    {
      "id": 1,
      "rule_id": "Rule 16",
      "content": "...",
      "similarity": 0.87
    }
  ],
  "metadata": {
    "match_count": 5,
    "embedding_dim": 768
  }
}
```

### 데이터 관리

```bash
# 데이터 검증
python verify_data.py

# 연결 테스트
python test_connection.py

# 특정 PDF만 처리하려면 etl_tennis_supabase.py 수정:
# target_docs 리스트에서 원하는 문서만 남기기
```

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
