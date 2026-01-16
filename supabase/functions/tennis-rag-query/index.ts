// ====================================
// Tennis Rules RAG - Edge Function
// ====================================
// 사용자 질문 → Gemini 임베딩 → 벡터 검색 → 답변 생성

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.0";

// CORS 헤더
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-gemini-api-key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

interface RequestBody {
  question: string;
  gemini_api_key: string;
  match_count?: number;
  match_threshold?: number;
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
    const { question, gemini_api_key, match_count = 5, match_threshold = 0.3 }: RequestBody = await req.json();

    if (!question || !gemini_api_key) {
      return new Response(
        JSON.stringify({ error: "question과 gemini_api_key가 필요합니다." }),
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
    const supabaseClient = createClient(
      Deno.env.get("SUPABASE_URL") ?? "",
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? ""
    );

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
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${gemini_api_key}`,
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
