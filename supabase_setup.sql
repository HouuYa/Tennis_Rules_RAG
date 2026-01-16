-- ====================================
-- Tennis Rules RAG - Supabase Setup
-- ====================================
-- 이 스크립트는 Supabase SQL Editor에서 실행하세요.
--
-- 📌 사용 방법:
-- 1. Supabase 대시보드 → SQL Editor 접속
-- 2. 이 파일 내용 전체 복사 & 붙여넣기
-- 3. Run 버튼 클릭
--
-- 💡 팁:
-- - 처음 설정 시: 전체 실행
-- - 테이블 초기화 필요 시: 아래 DROP TABLE 주석 해제
-- - RLS 정책이 필요 없으면: 5번 섹션 주석 처리
-- ====================================

-- ====================================
-- 0. 테이블 초기화 (선택사항)
-- ====================================
-- ⚠️ 경고: 아래 주석을 해제하면 기존 데이터가 모두 삭제됩니다!
-- DROP TABLE IF EXISTS tennis_rules CASCADE;

-- ====================================
-- 1. pgvector 확장 활성화
-- ====================================
CREATE EXTENSION IF NOT EXISTS vector;

-- ====================================
-- 2. tennis_rules 테이블 생성
-- ====================================
CREATE TABLE IF NOT EXISTS tennis_rules (
  id BIGSERIAL PRIMARY KEY,
  source_file TEXT NOT NULL,          -- 출처 파일명 (예: "ITF_Rules_2025_EN.pdf")
  rule_id TEXT NOT NULL,              -- 규칙 조항 ID (예: "Rule 1", "규칙 1")
  content TEXT NOT NULL,              -- 조항 내용 (검색 대상)
  metadata JSONB,                     -- 추가 메타데이터 (JSON 형식)
  embedding VECTOR(768),              -- Gemini Embeddings (768차원)
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================================
-- 3. 벡터 검색 인덱스 생성
-- ====================================

-- 옵션 A: 코사인 유사도 인덱스 (추천)
-- - 직관적이고 일반적으로 사용됨
-- - 벡터 크기에 무관하게 방향만 비교
CREATE INDEX IF NOT EXISTS tennis_rules_embedding_cosine_idx
ON tennis_rules
USING hnsw (embedding vector_cosine_ops);

-- 옵션 B: 내적(Inner Product) 인덱스
-- - 정규화된 벡터에서는 코사인 유사도와 동일
-- - 약간 더 빠를 수 있음
-- - ETL 스크립트에서 정규화하므로 사용 가능
-- CREATE INDEX IF NOT EXISTS tennis_rules_embedding_ip_idx
-- ON tennis_rules
-- USING hnsw (embedding vector_ip_ops);

-- 💡 참고: 둘 중 하나만 선택하세요!
-- 코사인 유사도를 사용하려면 위 인덱스를, 내적을 사용하려면 아래를 활성화하세요.

-- ====================================
-- 4. 추가 인덱스 (필터링 검색용)
-- ====================================
CREATE INDEX IF NOT EXISTS tennis_rules_rule_id_idx ON tennis_rules(rule_id);
CREATE INDEX IF NOT EXISTS tennis_rules_source_file_idx ON tennis_rules(source_file);

-- ====================================
-- 5. 벡터 유사도 검색 함수
-- ====================================

-- 옵션 A: 코사인 유사도 검색 함수 (추천)
-- 위에서 cosine 인덱스를 선택했다면 이 함수 사용
CREATE OR REPLACE FUNCTION match_tennis_rules(
  query_embedding VECTOR(768),
  match_threshold FLOAT DEFAULT 0.3,
  match_count INT DEFAULT 10
)
RETURNS TABLE (
  id BIGINT,
  source_file TEXT,
  rule_id TEXT,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    tennis_rules.id,
    tennis_rules.source_file,
    tennis_rules.rule_id,
    tennis_rules.content,
    tennis_rules.metadata,
    -- 코사인 거리를 유사도로 변환 (1 - 거리 = 유사도)
    1 - (tennis_rules.embedding <=> query_embedding) AS similarity
  FROM tennis_rules
  WHERE 1 - (tennis_rules.embedding <=> query_embedding) > match_threshold
  ORDER BY tennis_rules.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- 옵션 B: 내적(Inner Product) 검색 함수
-- 위에서 ip 인덱스를 선택했다면 이 함수로 교체
-- CREATE OR REPLACE FUNCTION match_tennis_rules(
--   query_embedding VECTOR(768),
--   match_threshold FLOAT DEFAULT 0.3,
--   match_count INT DEFAULT 10
-- )
-- RETURNS TABLE (
--   id BIGINT,
--   source_file TEXT,
--   rule_id TEXT,
--   content TEXT,
--   metadata JSONB,
--   similarity FLOAT
-- )
-- LANGUAGE plpgsql
-- AS $$
-- BEGIN
--   RETURN QUERY
--   SELECT
--     tennis_rules.id,
--     tennis_rules.source_file,
--     tennis_rules.rule_id,
--     tennis_rules.content,
--     tennis_rules.metadata,
--     -- 내적 거리를 유사도로 변환
--     1 - (tennis_rules.embedding <#> query_embedding) AS similarity
--   FROM tennis_rules
--   WHERE 1 - (tennis_rules.embedding <#> query_embedding) > match_threshold
--   ORDER BY tennis_rules.embedding <#> query_embedding
--   LIMIT match_count;
-- END;
-- $$;

-- 💡 연산자 설명:
-- <=>  : 코사인 거리 (cosine distance)
-- <#>  : 내적 거리 (inner product, negative dot product)
-- <->  : L2 거리 (유클리드 거리)

-- ====================================
-- 6. RLS (Row Level Security) 정책
-- ====================================
-- 💡 RLS를 사용하면 보안이 강화되지만, 간단한 프로젝트에서는 생략 가능
-- 필요 없으면 이 섹션 전체를 주석 처리하세요.

ALTER TABLE tennis_rules ENABLE ROW LEVEL SECURITY;

-- 모든 사용자가 읽기 가능 (익명 포함)
CREATE POLICY "Public read access"
ON tennis_rules
FOR SELECT
USING (true);

-- Service Role만 쓰기 가능 (ETL 스크립트용)
CREATE POLICY "Service role write access"
ON tennis_rules
FOR INSERT
WITH CHECK (true);

-- 업데이트 정책 (필요시 활성화)
-- CREATE POLICY "Service role update access"
-- ON tennis_rules
-- FOR UPDATE
-- USING (true)
-- WITH CHECK (true);

-- 삭제 정책 (필요시 활성화)
-- CREATE POLICY "Service role delete access"
-- ON tennis_rules
-- FOR DELETE
-- USING (true);

-- ====================================
-- 7. 테이블 및 함수 설명 (메타데이터)
-- ====================================
COMMENT ON TABLE tennis_rules IS '테니스 규칙 RAG 시스템 - 조항별 임베딩 저장';
COMMENT ON COLUMN tennis_rules.source_file IS '출처 파일명 (예: ITF_Rules_2025_EN.pdf)';
COMMENT ON COLUMN tennis_rules.rule_id IS '규칙 조항 ID (예: Rule 1, 규칙 1)';
COMMENT ON COLUMN tennis_rules.content IS '검색 대상 텍스트 (조항 내용)';
COMMENT ON COLUMN tennis_rules.metadata IS '추가 메타데이터 (JSON 형식)';
COMMENT ON COLUMN tennis_rules.embedding IS 'Gemini Embeddings 벡터 (768차원)';
COMMENT ON FUNCTION match_tennis_rules IS '질문 임베딩과 유사한 테니스 규칙 검색 (코사인 유사도)';

-- ====================================
-- 8. 유틸리티 쿼리 (테스트 및 확인용)
-- ====================================

-- 전체 레코드 수 확인
-- SELECT COUNT(*) AS total_rules FROM tennis_rules;

-- 파일별 레코드 분포
-- SELECT
--   source_file,
--   COUNT(*) as count
-- FROM tennis_rules
-- GROUP BY source_file;

-- 최신 5개 레코드 확인
-- SELECT
--   id,
--   source_file,
--   rule_id,
--   LEFT(content, 100) AS content_preview,
--   created_at
-- FROM tennis_rules
-- ORDER BY created_at DESC
-- LIMIT 5;

-- 벡터 차원 확인
-- SELECT
--   id,
--   rule_id,
--   vector_dims(embedding) AS embedding_dimension
-- FROM tennis_rules
-- LIMIT 5;

-- 벡터 검색 테스트 (실제 임베딩 값으로 교체 필요)
-- SELECT * FROM match_tennis_rules(
--   '[0.1, 0.2, 0.3, ...]'::vector(768),
--   0.5,  -- 유사도 임계값
--   5     -- 결과 개수
-- );

-- ====================================
-- ✅ 설정 완료!
-- ====================================
--
-- 다음 단계:
-- 1. ETL 스크립트 실행: python etl_tennis_supabase.py
-- 2. 데이터 확인: 위의 유틸리티 쿼리 실행
-- 3. Edge Function 배포: supabase functions deploy tennis-rag-query
-- 4. 웹 UI 실행: python -m http.server 8000
--
-- 📚 문서:
-- - SETUP_GUIDE.md: 상세 설정 가이드
-- - README.md: 프로젝트 개요
-- - CODE_REVIEW.md: 코드 점검 결과
--
-- 🆘 문제 발생 시:
-- - test_connection.py 실행하여 환경 확인
-- - SETUP_GUIDE.md의 "문제 해결" 섹션 참고
-- ====================================
