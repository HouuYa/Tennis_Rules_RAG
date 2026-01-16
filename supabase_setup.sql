-- ====================================
-- Tennis Rules RAG - Supabase Setup
-- ====================================
-- 이 스크립트는 Supabase SQL Editor에서 실행하세요.

-- 1. pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. tennis_rules 테이블 생성 (이미 있다면 스킵)
CREATE TABLE IF NOT EXISTS tennis_rules (
  id BIGSERIAL PRIMARY KEY,
  source_file TEXT,
  rule_id TEXT,
  content TEXT NOT NULL,
  metadata JSONB,
  embedding VECTOR(768),  -- Gemini embedding 차원
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 벡터 검색 성능을 위한 인덱스 생성
-- HNSW 인덱스: 고속 벡터 유사도 검색 (내적 거리 사용)
CREATE INDEX IF NOT EXISTS tennis_rules_embedding_idx
ON tennis_rules
USING hnsw (embedding vector_ip_ops);

-- 추가 인덱스: rule_id, source_file로 필터링 검색
CREATE INDEX IF NOT EXISTS tennis_rules_rule_id_idx ON tennis_rules(rule_id);
CREATE INDEX IF NOT EXISTS tennis_rules_source_file_idx ON tennis_rules(source_file);

-- 4. 벡터 유사도 검색 함수 (내적 기반)
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
    -- 내적(inner product) 기반 유사도 (정규화된 벡터이므로 코사인 유사도와 동일)
    1 - (tennis_rules.embedding <#> query_embedding) AS similarity
  FROM tennis_rules
  WHERE 1 - (tennis_rules.embedding <#> query_embedding) > match_threshold
  ORDER BY tennis_rules.embedding <#> query_embedding
  LIMIT match_count;
END;
$$;

-- 5. RLS (Row Level Security) 정책 설정 (선택사항)
-- 익명 사용자도 읽기 가능하도록 설정
ALTER TABLE tennis_rules ENABLE ROW LEVEL SECURITY;

-- 모든 사용자가 읽기 가능
CREATE POLICY "Public read access"
ON tennis_rules
FOR SELECT
USING (true);

-- Service Role만 쓰기 가능 (ETL 스크립트용)
CREATE POLICY "Service role write access"
ON tennis_rules
FOR INSERT
WITH CHECK (true);

-- 6. 데이터 확인 쿼리
-- SELECT COUNT(*) FROM tennis_rules;
-- SELECT id, source_file, rule_id, LEFT(content, 100) FROM tennis_rules LIMIT 5;

-- 7. 벡터 검색 테스트 (임베딩 값은 실제 값으로 교체 필요)
-- SELECT * FROM match_tennis_rules(
--   '[0.1, 0.2, ..., 0.3]'::vector(768),
--   0.5,
--   5
-- );

COMMENT ON TABLE tennis_rules IS '테니스 규칙 RAG 데이터베이스 - 조항별 임베딩 저장';
COMMENT ON FUNCTION match_tennis_rules IS '질문 임베딩과 유사한 규칙 검색 (내적 기반)';
