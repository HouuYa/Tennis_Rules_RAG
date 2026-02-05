# 🎾 Tennis Rules RAG 시스템 설정 가이드

## 📋 목차
1. [시스템 개요](#시스템-개요)
2. [사전 준비](#사전-준비)
3. [Supabase 설정](#supabase-설정)
4. [ETL 실행](#etl-실행)
5. [Edge Function 배포](#edge-function-배포)
6. [프론트엔드 실행](#프론트엔드-실행)
7. [문제 해결](#문제-해결)

---

## 시스템 개요

### 아키텍처
```
PDF 문서 → ETL 스크립트 → Supabase (pgvector)
                              ↓
사용자 질문 → Edge Function → RAG 검색 → Gemini 답변
```

### 주요 기능
- ✅ **답변 생성**: Gemini 1.5 Flash (gemini-flash-latest)로 컨텍스트 기반 답변
- ✅ **API 키 관리**: 클라이언트 우선순위 (RequestBody > Env)
- ✅ 테니스 규칙 PDF 자동 처리 (한글/영문)
- ✅ **조항별 Chunking**: 정규식 기반 + TOC 제외 로직 적용 (전체 155개 조항)
  - 한글: "**1. 제목**", "**I. 제목**", "**A. 제목**"
  - 영문: "**Rule 1**", "**Article 1**", "**Appendix I**"
- ✅ 사용자 API 키 재사용 (AI Coach와 동일)
- ✅ 실시간 채팅 UI

---

## 사전 준비

### 1. 필수 계정
- [ ] Supabase 계정 (https://supabase.com)
- [ ] Google Cloud 계정 (Gemini API용)

### 2. API 키 발급

#### Gemini API Key 발급
1. https://makersuite.google.com/app/apikey 접속
2. "Create API Key" 클릭
3. 프로젝트 선택 또는 생성
4. 생성된 API 키 복사

#### Supabase Keys 확인
1. Supabase 프로젝트 대시보드 접속
2. Settings → API 메뉴로 이동
3. 아래 키 복사:
   - `Project URL` (SUPABASE_URL)
   - `service_role` secret key (SUPABASE_SERVICE_KEY)

### 3. 로컬 환경 설정

#### Python 환경 (ETL용)
```bash
# Python 3.8+ 필요
python --version

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

#### Supabase CLI (Edge Function 배포용)
```bash
# macOS
brew install supabase/tap/supabase

# Windows (scoop 사용)
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase

# Linux
brew install supabase/tap/supabase
```

---

## Supabase 설정

### 1. pgvector 확장 및 테이블 생성

1. Supabase 대시보드에서 **SQL Editor** 열기
2. `supabase_setup.sql` 파일 내용 전체 복사
3. SQL Editor에 붙여넣기
4. **Run** 버튼 클릭

✅ 실행 결과:
- `vector` 확장 활성화
- `tennis_rules` 테이블 생성
- HNSW 인덱스 생성
- `match_tennis_rules` 함수 생성
- RLS 정책 설정

### 2. 테이블 확인
```sql
-- SQL Editor에서 실행
SELECT COUNT(*) FROM tennis_rules;
SELECT * FROM tennis_rules LIMIT 5;
```

처음에는 0건이 정상입니다 (ETL 실행 후 데이터 생성).

---

## ETL 실행

### 1. 환경 변수 설정

`.env` 파일을 편집하여 실제 API 키 입력:

```env
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SERVICE_KEY="eyJhbGc..."
GEMINI_API_KEY="AIzaSyC..."
```

⚠️ **주의**: `.env` 파일은 절대 Git에 커밋하지 마세요!

# 전체 실행 (자동화된 경우)
python etl_tennis_supabase.py

# 또는 더 세밀한 제어 (추천):
python gen_sql_from_txt.py  # 텍스트에서 SQL 생성 (임베딩 포함)
python upload_rules.py      # Supabase로 데이터 업로드
```

### 3. 선택적 옵션

```bash
# 드라이 런 (DB에 쓰지 않고 테스트만)
DRY_RUN=1 python etl_tennis_supabase.py

# 임베딩 생성 스킵 (청크 분할만 테스트)
SKIP_EMBEDDING=1 python etl_tennis_supabase.py

# 원격 파일 다운로드 스킵 (로컬 PDF만 처리)
SKIP_REMOTE=1 python etl_tennis_supabase.py
```

### 4. 실행 결과 확인

```bash
# 로그 예시
[INFO] 🔥 ETL 프로세스 시작
[INFO] 📖 텍스트 추출 중: ./테니스규정집(2020.11.20 개정판).pdf
[INFO] ✂️  Chunking 완료: 156개 조항 생성
[INFO] 🚀 Supabase 업로드 시작 (총 156개, 배치 사이즈 10)
[INFO] ✅ 파일 처리 완료: 테니스규정집(2020.11.20 개정판).pdf
[INFO] 🎉 모든 작업이 완료되었습니다.
```

Supabase에서 확인:
```sql
SELECT
  source_file,
  COUNT(*) as chunk_count
FROM tennis_rules
GROUP BY source_file;
```

---

## Edge Function 배포

### 1. Supabase CLI 로그인

```bash
supabase login
```

브라우저에서 인증 후 토큰이 자동 저장됩니다.

### 2. 프로젝트 연결

```bash
# 프로젝트 ID 확인: Supabase 대시보드 → Settings → General
supabase link --project-ref your-project-id
```

### 3. Edge Function 배포

```bash
# tennis-rag-query 함수 배포
supabase functions deploy tennis-rag-query

# 배포 완료 후 URL 확인
# https://your-project.supabase.co/functions/v1/tennis-rag-query
```

### 4. 환경 변수 설정 (Edge Function용)

```bash
# Supabase URL과 Service Role Key는 자동 설정됨
# 추가 환경 변수가 필요한 경우:
supabase secrets set MY_SECRET=value
```

### 5. 함수 테스트

```bash
curl -X POST \
  https://your-project.supabase.co/functions/v1/tennis-rag-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "서브 폴트는 어떤 경우인가요?",
    "gemini_api_key": "YOUR_GEMINI_API_KEY"
  }'
```

---

## 프론트엔드 실행

### 1. HTML 파일 수정

`tennis_chat.html` 파일을 열어 Edge Function URL 수정:

```javascript
// 19번째 줄 근처
const EDGE_FUNCTION_URL = 'https://your-project.supabase.co/functions/v1/tennis-rag-query';
```

### 2. 로컬 서버 실행

```bash
# Python 간단 서버
python -m http.server 8000

# 또는 Node.js
npx http-server -p 8000
```

### 3. 브라우저 접속

http://localhost:8000/tennis_chat.html

### 4. 사용 방법

1. **Gemini API Key 입력**
   - AI Coach에서 사용하는 것과 동일한 키
   - 브라우저 로컬 스토리지에만 저장됨

2. **질문 입력**
   ```
   예시:
   - 서브 폴트는 어떤 경우인가요?
   - 타이브레이크 규칙을 알려주세요
   - Let이란 무엇인가요?
   ```

3. **답변 확인**
   - AI 답변과 함께 참고 규칙 조항 표시
   - 유사도 점수 확인 가능

---

## 문제 해결

### 1. ETL 실행 오류

#### "GEMINI_API_KEY가 비어있거나 플레이스홀더로 보입니다"
```bash
# .env 파일에서 실제 API 키로 교체 필요
GEMINI_API_KEY="AIzaSyC..."  # "your-google-gemini-api-key" 제거
```

#### "supabase client 초기화 실패"
```bash
# supabase-py 재설치
pip uninstall supabase
pip install supabase --upgrade
```

#### PDF 파일이 없음
```bash
# 파일 경로 확인
ls -la *.pdf

# 또는 다운로드
curl -O "https://www.itftennis.com/media/7221/2025-rules-of-tennis-english.pdf"
```

### 2. Edge Function 오류

#### 배포 실패
```bash
# Supabase CLI 업데이트
brew upgrade supabase

# 재로그인
supabase logout
supabase login
```

#### CORS 오류
- `index.ts`의 `corsHeaders`에 도메인 추가
- Supabase 대시보드 → Authentication → URL Configuration 확인

#### 타임아웃
- Gemini API 응답이 느린 경우
- Edge Function 타임아웃 설정 조정

### 3. 검색 결과 없음

#### 임베딩 차원 불일치
```sql
-- 벡터 차원 확인
SELECT
  id,
  rule_id,
  vector_dims(embedding) as dim
FROM tennis_rules
LIMIT 5;

-- 모두 768이어야 함
```

#### 유사도 임계값 조정
```javascript
// tennis_chat.html에서
match_threshold: 0.1  // 0.3 → 0.1로 낮춤
```

### 4. 성능 최적화

#### 인덱스 재구축
```sql
-- HNSW 인덱스 재생성
REINDEX INDEX tennis_rules_embedding_idx;
```

#### 배치 크기 조정
```python
# etl_tennis_supabase.py 179번째 줄
batch_size = 20  # 10 → 20으로 증가
```

---

## 다음 단계

### 1. 프로덕션 배포
- [ ] Vercel/Netlify에 HTML 배포
- [ ] 환경 변수 보안 강화
- [ ] Rate limiting 설정

### 2. 기능 확장
- [ ] 채팅 히스토리 저장
- [ ] 멀티턴 대화 지원
- [ ] 이미지/다이어그램 추가
- [ ] 다국어 지원 (영어/한국어 자동 감지)

### 3. 모니터링
- [ ] Supabase 로그 확인
- [ ] API 사용량 모니터링
- [ ] 검색 품질 평가

---

## 📅 점검 일자
2026-02-05
- [Supabase pgvector](https://supabase.com/docs/guides/ai/vector-columns)
- [Gemini API](https://ai.google.dev/docs)
- [Supabase Edge Functions](https://supabase.com/docs/guides/functions)

## 🆘 지원

문제가 발생하면 GitHub Issues에 등록하거나 이메일로 문의하세요.

---

✨ **Happy RAGing!** 🎾
