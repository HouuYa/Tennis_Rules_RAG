import re
import json
from supabase import create_client, Client
from tqdm import tqdm

url = "https://ctzcgrwjsrvoxjycwtya.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0emNncndqc3J2b3hqeWN3dHlhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjcxMDAzNjAsImV4cCI6MjA4MjY3NjM2MH0.Ni2obAqCCy1ARBy2BxG8sz1Pcbh4exIZS726VsLwOS8"

supabase = create_client(url, key)

def parse_sql(filename):
    print(f"Reading {filename}...")
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Parsing content...")
    # Regex to capture the 4 fields: source, rule_id, content, embedding
    # VALUES ('...', '...', '...', '...'::vector);
    # handle escaped quotes ''
    pattern = re.compile(r"VALUES \('((?:[^']|'')*)', '((?:[^']|'')*)', '((?:[^']|'')*)', '((?:[^']|'')*)'::vector\)", re.DOTALL)
    
    matches = pattern.findall(content)
    print(f"Found {len(matches)} matches.")
    
    data = []
    for m in matches:
        source = m[0].replace("''", "'")
        rule = m[1].replace("''", "'")
        text = m[2].replace("''", "'")
        emb_str = m[3] 
        
        try:
            embedding = json.loads(emb_str)
        except json.JSONDecodeError:
            print(f"Failed to parse embedding for {rule}")
            continue
        
        data.append({
            "source_file": source,
            "rule_id": rule,
            "content": text,
            "embedding": embedding
        })
    return data

def upload(data):
    print(f"Uploading {len(data)} records...")
    # Clean up test data if possible
    try:
        supabase.table("tennis_rules").delete().eq("rule_id", "TEST_ANON").execute()
    except:
        pass

    batch_size = 10
    success_count = 0
    for i in tqdm(range(0, len(data), batch_size)):
        batch = data[i:i+batch_size]
        try:
            supabase.table("tennis_rules").insert(batch).execute()
            success_count += len(batch)
        except Exception as e:
            print(f"Error on batch {i}: {e}")
            # Try one by one if batch fails
            for item in batch:
                try:
                    supabase.table("tennis_rules").insert(item).execute()
                    success_count += 1
                except Exception as inner_e:
                    print(f"Error on item {item['rule_id']}: {inner_e}")
                    
    print(f"Successfully uploaded {success_count} records.")

if __name__ == "__main__":
    try:
        data = parse_sql("insert_rules.sql")
        if data:
            upload(data)
    except Exception as e:
        print(f"Fatal error: {e}")
