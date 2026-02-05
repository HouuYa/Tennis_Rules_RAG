// ====================================
// Tennis Rules RAG - Edge Function
// ====================================
// 사용자 질문 → Gemini 임베딩 → 벡터 검색 → 답변 생성

import { serve } from "https://deno.land/std@0.224.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.43.4";

// CORS 헤더
// 프로덕션: ALLOWED_ORIGIN 환경 변수로 특정 도메인 제한 권장
// 로컬 개발: "*" fallback 사용
const corsHeaders = {
  "Access-Control-Allow-Origin": Deno.env.get("ALLOWED_ORIGIN") ?? "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-gemini-api-key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

interface RequestBody {
  question: string;
  match_count?: number;
  match_threshold?: number;
  gemini_api_key?: string;
}

interface SearchResult {
  id: number;
  source_file: string;
  rule_id: string;
  content: string;
  metadata: any;
  similarity: number;
}

serve(async (req) => {
  // OPTIONS 요청 처리 (CORS preflight)
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    // 1. 요청 파라미터 추출
    const { question, match_count = 5, match_threshold = 0.3, gemini_api_key: client_api_key }: RequestBody = await req.json();

    // API 키 결정: 클라이언트 제공 값 우선 -> 서버 환경 변수 fallback
    const gemini_api_key = client_api_key || Deno.env.get("GEMINI_API_KEY");

    if (!question) {
      return new Response(
        JSON.stringify({ error: "question이 필요합니다." }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    if (!gemini_api_key) {
      console.error("[RAG] GEMINI_API_KEY가 제공되지 않았습니다.");
      return new Response(
        JSON.stringify({ error: "Gemini API 키가 필요합니다 (클라이언트 제공 또는 서버 설정)." }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    console.log(`[RAG] 질문: ${question}`);

    // 2. Gemini API로 질문 임베딩 생성
    const embeddingResponse = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key=${gemini_api_key}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "models/gemini-embedding-001",
          content: {
            parts: [{ text: question }]
          },
          taskType: "RETRIEVAL_QUERY",
          outputDimensionality: 768
        })
      }
    );

    if (!embeddingResponse.ok) {
      const errorText = await embeddingResponse.text();
      console.error("[RAG] Gemini API 오류:", errorText);
      return new Response(
        JSON.stringify({ error: "Gemini API 호출 실패", details: errorText }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const embeddingData = await embeddingResponse.json();
    const queryEmbedding = embeddingData?.embedding?.values;

    if (!queryEmbedding || !Array.isArray(queryEmbedding)) {
      console.error("[RAG] 임베딩 추출 실패:", embeddingData);
      return new Response(
        JSON.stringify({ error: "임베딩 생성 실패" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    console.log(`[RAG] 임베딩 생성 완료: ${queryEmbedding.length}차원`);

    // 3. Supabase에서 유사 문서 검색
    const supabaseUrl = Deno.env.get("SUPABASE_URL");
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");

    if (!supabaseUrl || !supabaseServiceKey) {
      console.error("[RAG] Supabase 환경 변수가 설정되지 않았습니다.");
      return new Response(
        JSON.stringify({ error: "서버 설정 오류: Supabase 환경 변수 누락" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabaseClient = createClient(supabaseUrl, supabaseServiceKey);

    const { data: searchResults, error: searchError } = await supabaseClient.rpc(
      "match_tennis_rules",
      {
        query_embedding: queryEmbedding,
        match_threshold: match_threshold,
        match_count: match_count
      }
    );

    if (searchError) {
      console.error("[RAG] 검색 오류:", searchError);
      return new Response(
        JSON.stringify({ error: "벡터 검색 실패", details: searchError }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    console.log(`[RAG] 검색 완료: ${searchResults?.length || 0}개 결과`);

    // 4. 컨텍스트 구성
    const context = (searchResults as SearchResult[])
      ?.map((r, idx) => `[${idx + 1}] ${r.rule_id}\n${r.content}\n(유사도: ${r.similarity.toFixed(3)})`)
      .join("\n\n---\n\n");

    // 5. Gemini로 답변 생성 (Optional - 프론트엔드에서도 가능)
    const generateResponse = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=${gemini_api_key}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{
            parts: [{
              text: `당신은 테니스 규칙 전문가입니다. 아래 규칙을 참고하여 질문에 답변하세요.

## 테니스 규칙 참고 자료:
${context}

## 질문:
${question}

## 답변 지침:
- 위 규칙을 바탕으로 정확하게 답변하세요
- 해당 규칙의 조항(rule_id)을 명시하세요
- 규칙에 없는 내용은 "관련 규칙을 찾을 수 없습니다"라고 답변하세요
- 한국어로 자세히 설명하세요`
            }]
          }],
          generationConfig: {
            temperature: 0.2,
            maxOutputTokens: 1024
          }
        })
      }
    );

    let answer = "답변 생성 실패";
    if (generateResponse.ok) {
      const generateData = await generateResponse.json();
      answer = generateData?.candidates?.[0]?.content?.parts?.[0]?.text || "답변을 생성할 수 없습니다.";
    }

    // 6. 응답 반환
    return new Response(
      JSON.stringify({
        question,
        answer,
        sources: searchResults,
        metadata: {
          match_count: searchResults?.length || 0,
          embedding_dim: queryEmbedding.length
        }
      }),
      {
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      }
    );

  } catch (error) {
    console.error("[RAG] 처리 오류:", error);
    return new Response(
      JSON.stringify({ error: "서버 오류", details: error.message }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
