# 🎾 Tennis Rules RAG 상세 설정 가이드

이 문서는 프로젝트 설치, 데이터 적재, 그리고 배포를 위한 단계별 지침을 제공합니다.

---

## 🛠️ 개발 환경 설정

### 1. 전제 조건
- Python 3.8 이상
- Supabase 계정 및 프로젝트
- Google Gemini API Key

### 2. 라이브러리 설치
```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 3. 환경 변수 설정 (`.env`)
프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 입력합니다.
```env
SUPABASE_URL="자신의_supabase_url"
SUPABASE_SERVICE_KEY="자신의_service_role_key"
GEMINI_API_KEY="자신의_gemini_api_key"
```

⚠️ **주의**: `.env` 파일은 절대 Git에 커밋하지 마세요!

### 3. 선택적 옵션 (Advanced)

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

## 🗄️ 데이터베이스 및 백엔드 설정

### 1. Supabase 테이블 생성
`supabase_setup.sql`의 내용을 Supabase SQL Editor에서 실행합니다. 이는 `pgvector` 확장을 활성화하고 `tennis_rules` 테이블과 검색용 RPC 함수를 생성합니다.

### 2. Edge Function 배포
관리자 및 질의응답을 위한 서버리스 함수를 배포합니다.
```bash
supabase login
supabase link --project-ref your-project-ref
# Function에서 사용할 비밀 키 설정 (필수!)
supabase secrets set SUPABASE_URL=your_supabase_url SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
supabase functions deploy tennis-rag-query
supabase functions deploy tennis-etl
```

---

## 🚀 ETL 프로세스 (데이터 적재)

새로운 테니스 규칙 PDF를 시스템에 추가하려면 다음 과정을 거칩니다.

1.  **텍스트 추출**: `python extract_pdf_gemini.py` (PDF -> txt)
2.  **SQL 생성**: `python gen_sql_from_txt.py` (txt -> sql + embeddings)
3.  **데이터 소거**: (필요시) Admin 페이지 또는 SQL에서 기존 데이터를 삭제합니다.
4.  **최종 업로드**: `python upload_rules.py` (sql -> Supabase)

---

## 🌐 웹 인터페이스 및 배포

### 1. 로컬 실행
`tennis_chat.html` 파일 내의 `EDGE_FUNCTION_URL`을 본인의 URL로 수정한 후 실행합니다.
```bash
python -m http.server 8000
```

### 2. Admin Dashboard 사용법
- `admin.html`에 접속하여 현재 DB에 적재된 `source_file` 목록을 확인합니다.
- 특정 파일과 관련된 데이터를 삭제하거나 업로드 상태를 모니터링할 수 있습니다.

### 3. Netlify 배포
Netlify CLI를 사용하거나 웹 대시보드에서 수동 배포를 진행할 수 있습니다.
```bash
# 수동 배포 (CLI 사용 예시)
npx netlify deploy --dir . --prod
```

---

## 🆘 문제 해결 (FAQ)

**Q: 검색 결과가 나오지 않습니다.**
A: `tennis_rules` 테이블에 데이터가 있는지 확인하고, `match_threshold` 값을 조절해 보세요.

**Q: API Key 오류가 발생합니다.**
A: `.env` 파일의 키가 유효한지, 그리고 브라우저 UI에서 입력한 키가 정확한지 확인하세요.

---

*최종 업데이트: 2026-02-08*
