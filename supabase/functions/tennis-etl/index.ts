// ====================================
// Tennis Rules Admin ETL - Edge Function
// ====================================
// 데이터 관리 (삭제 및 업로드 상태 확인)

import { serve } from "https://deno.land/std@0.224.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.43.4";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
};

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabaseClient = createClient(supabaseUrl, supabaseServiceKey);

    const { action, fileName } = await req.json();

    if (action === "list_sources") {
      const { data, error } = await supabaseClient
        .from('tennis_rules')
        .select('source_file');

      if (error) throw error;
      const sources = [...new Set(data.map((item: any) => item.source_file))];
      return new Response(JSON.stringify({ sources }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    if (action === "delete_source") {
      if (!fileName) throw new Error("fileName is required for deletion");

      const { data, error } = await supabaseClient
        .from('tennis_rules')
        .delete()
        .eq('source_file', fileName);

      if (error) throw error;
      return new Response(JSON.stringify({ message: `Successfully deleted ${fileName}` }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    return new Response(JSON.stringify({ error: "Invalid action" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" }
    });

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" }
    });
  }
});
