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
    const supabaseUrl = Deno.env.get("SUPABASE_URL");
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    // const authAdminKey = Deno.env.get("AUTH_ADMIN_KEY"); // Future improvement: Use environment variable
    // For now, using a simple check against the Service Role Key or a dedicated secret is recommended.
    // However, since the client (admin.html) sends the Service Role Key as 'apikey' (based on previous setup guide instructions which were risky but functional for this "admin" context),
    // we should ideally transition to a separate admin key.

    // To fix the immediate "No Authentication" vulnerability reported:
    // We will require the 'x-admin-key' header to match the Service Role Key (as the admin is the only one who should have it).
    // Note: Sharing Service Role Key with client is BAD practice.
    // Better practice: User Auth (Supabase Auth) -> Check if user is admin.
    // Current "Quick Fix" for existing architecture: Check for a specific secret header.

    if (!supabaseUrl || !supabaseServiceKey) {
      console.error("Missing environment variables: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY");
      throw new Error("Server configuration error: Missing environment variables.");
    }

    // AUTH CHECK
    // In a real production app, use Supabase Auth (getUser).
    // Here, we enforce that the request MUST have the Service Role Key in the Authorization (or custom) header to prove it is an admin operation.
    // Since admin.html uses Anon Key by default, we need to update admin.html to prompt for an Admin Key (Service Role Key) or a specific password.

    // Let's implement a simple "Admin Secret" check.
    const reqJson = await req.json();
    const { action, fileName, adminKey } = reqJson; // Expect adminKey in body

    if (adminKey !== supabaseServiceKey) {
      console.error("[tennis-etl] Unauthorized access attempt.");
      return new Response(JSON.stringify({ error: "Unauthorized: Invalid Admin Key" }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    const supabaseClient = createClient(supabaseUrl, supabaseServiceKey);
    console.log(`[tennis-etl] Received action: ${action}, fileName: ${fileName}`);

    if (action === "list_sources") {
      const { data, error } = await supabaseClient
        .from('tennis_rules')
        .select('source_file');

      if (error) {
        console.error("[tennis-etl] Database error:", error);
        throw error;
      }

      const sources = [...new Set(data.map((item: any) => item.source_file))];
      console.log(`[tennis-etl] Found ${sources.length} unique sources.`);

      return new Response(JSON.stringify({ sources }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    if (action === "delete_source") {
      if (!fileName) throw new Error("fileName is required for deletion");

      console.log(`[tennis-etl] Deleting source: ${fileName}`);
      const { data, error, count } = await supabaseClient
        .from('tennis_rules')
        .delete({ count: 'exact' })
        .eq('source_file', fileName);

      if (error) {
        console.error("[tennis-etl] Delete error:", error);
        throw error;
      }

      console.log(`[tennis-etl] Deleted rows count: ${count}`);
      return new Response(JSON.stringify({ message: `Successfully deleted ${fileName}` }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    return new Response(JSON.stringify({ error: "Invalid action" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" }
    });

  } catch (error) {
    console.error("[tennis-etl] Unhandled error:", error.message);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" }
    });
  }
});
