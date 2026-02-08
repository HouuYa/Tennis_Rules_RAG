import os
import re
import json
from dotenv import load_dotenv
from supabase import create_client, Client
from tqdm import tqdm

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

if not url or not key:
    raise ValueError("SUPABASE_URL or SUPABASE_SERVICE_KEY not found in environment")

supabase = create_client(url, key)

def parse_sql(filename):
    print(f"Reading {filename}...")
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Parsing content...")
    # Regex to capture the 5 fields: source, rule_id, content, metadata, embedding
    # VALUES ('...', '...', '...', '...'::jsonb, '...'::vector);
    pattern = re.compile(r"VALUES \('((?:[^']|'')*)', '((?:[^']|'')*)', '((?:[^']|'')*)', '((?:[^']|'')*)'::jsonb, '((?:[^']|'')*)'::vector\)", re.DOTALL)
    
    matches = pattern.findall(content)
    print(f"Found {len(matches)} matches.")
    
    data = []
    for m in matches:
        source = m[0].replace("''", "'")
        rule = m[1].replace("''", "'")
        text = m[2].replace("''", "'")
        meta_str = m[3].replace("''", "'")
        emb_str = m[4] 
        
        try:
            embedding = json.loads(emb_str)
            metadata = json.loads(meta_str)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON for {rule}: {e}")
            continue
        
        data.append({
            "source_file": source,
            "rule_id": rule,
            "content": text,
            "metadata": metadata,
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
        data = parse_sql("insert_rules_en.sql")
        if data:
            upload(data)
    except Exception as e:
        print(f"Fatal error: {e}")
