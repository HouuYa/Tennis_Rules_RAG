import os
from supabase import create_client, Client
import json

url = "https://ctzcgrwjsrvoxjycwtya.supabase.co"
# Anon key from get_publishable_keys
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0emNncndqc3J2b3hqeWN3dHlhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjcxMDAzNjAsImV4cCI6MjA4MjY3NjM2MH0.Ni2obAqCCy1ARBy2BxG8sz1Pcbh4exIZS726VsLwOS8"

supabase: Client = create_client(url, key)

try:
    print("Testing read...")
    data = supabase.table("tennis_rules").select("*").limit(1).execute()
    print("Read success:", data)
    
    print("Testing insert...")
    # Using a dummy rule_id that we can delete later
    dummy = {
        "source_file": "test_anon_check",
        "rule_id": "TEST_ANON",
        "content": "This is a test to check write permissions.",
        "embedding": [0.1]*768
    }
    
    res = supabase.table("tennis_rules").insert(dummy).execute()
    print("Insert success:", res)
    
except Exception as e:
    print("Error:", e)
