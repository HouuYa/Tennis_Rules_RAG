import os
import re
import google.generativeai as genai
import numpy as np
from tqdm import tqdm
import json
import time
from dotenv import load_dotenv

load_dotenv()

class SQLGenFromText:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        genai.configure(api_key=self.gemini_key)
        self.embedding_model = "models/gemini-embedding-001"
        self.embedding_dim = 768

    def load_text(self, txt_path):
        with open(txt_path, 'r', encoding='utf-8') as f:
            return f.read()

    def split_into_chunks(self, text, source_name):
        # 1. 목차(TOC)를 건너뛰고 실제 본문이 시작되는 지점 찾기
        # 한글: "1. 코트", "ITF 테니스 룰" | 영문: "1. THE COURT", "RULES OF TENNIS"
        start_marker = re.search(r"(\*\*1\.\s*코트|\*\*ITF\s*테니스\s*룰\*\*|1\.\s*THE\s*COURT|RULES\s*OF\s*TENNIS)", text, re.IGNORECASE)
        
        intro_text = ""
        body_text = text
        
        if start_marker:
            intro_text = text[:start_marker.start()]
            body_text = text[start_marker.start():]
            print(f"Body start found at character {start_marker.start()}")
        else:
            print("Warning: Could not find main body start marker. Using full text.")

        # 2. 본문에서 실제 규칙/섹션 헤더 찾기
        # 패턴 1: **1. 제목** (한글 규정집 스타일)
        # 패턴 2: 1. THE COURT 또는 APPENDIX I (영문 규정집 스타일)
        # 패턴 3: **FOREWORD** 등 특수 섹션
        body_split_pattern = re.compile(
            r"(\n\s*(?:"
            r"\*\*(?!(?:페이지|목차|표지|머리말))(?:\d+\.|[I-V]+\.|[A-Z]\.)\s*.*?\*\*|"  # **1. 코트**
            r"(?:\d+\.|APPENDIX\s+[IVX]+|RULE\s+\d+)\s+[A-Z\s]{3,}|"                # 1. THE COURT
            r"\*\*[A-Z\s]{3,}\*\*"                                                  # **FOREWORD**
            r")(\n|$))", 
            flags=re.IGNORECASE
        )
        
        parts = body_split_pattern.split(body_text)
        chunks = []
        
        # 인트로/머리말 추가 (필요시)
        if intro_text.strip():
            chunks.append({
                "source_file": source_name,
                "rule_id": "Foreword/Intro",
                "content": intro_text.strip()[:8000]
            })
            
        for i in range(1, len(parts), 3): # Groups of 3 because of nested captures in regex
            header = parts[i].strip()
            content = parts[i+2].strip() if i+2 < len(parts) else ""
            
            # Clean rule ID
            rule_id = header.replace("**", "").strip()
            
            # 만약 다음 규칙 전까지의 내용이 너무 길면 자르거나 처리 (여기서는 일단 통째로)
            full_content = f"{header}\n{content}"
            
            if len(full_content.strip()) > 30: # 너무 짧은 매칭(잘못된 매칭) 제외
                chunks.append({
                    "source_file": source_name,
                    "rule_id": rule_id,
                    "content": full_content
                })
        
        # 만약 본문에서 찾은게 없다면 (정규식 실패 방지)
        if not chunks and body_text.strip():
            chunks.append({
                "source_file": source_name,
                "rule_id": "Full Body (Fallback)",
                "content": body_text.strip()[:8000]
            })

        return chunks

    def generate_sql(self, chunks, output_file):
        print(f"Generating SQL for {len(chunks)} chunks...")
        with open(output_file, "w", encoding="utf-8") as f:
            for item in tqdm(chunks):
                # Retry loop for Gemini API (Rate Limits)
                max_retries = 5
                retry_delay = 2
                embedding = None
                
                for attempt in range(max_retries):
                    try:
                        # Get embedding
                        result = genai.embed_content(
                            model=self.embedding_model,
                            content=item["content"],
                            task_type="retrieval_document",
                            output_dimensionality=self.embedding_dim,
                        )
                        embedding = result['embedding']
                        break # Success
                    except Exception as e:
                        if "429" in str(e) or "Resource exhausted" in str(e):
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay)
                                retry_delay *= 2
                                continue
                        print(f"\nError processing {item.get('rule_id', 'unknown')}: {e}")
                        break
                
                if embedding is None:
                    continue

                try:
                    # Normalize (Gemini embeddings are usually unit length, but good to ensure)
                    vec_np = np.array(embedding, dtype=float)
                    norm = np.linalg.norm(vec_np)
                    if norm > 0:
                        vec_np = vec_np / norm
                    embedding_list = vec_np.tolist()
                    
                    content_esc = item["content"].replace("'", "''")
                    rule_id_esc = item["rule_id"].replace("'", "''")
                    source_esc = item["source_file"].replace("'", "''")
                    
                    # Postgres vector format is '[1,2,3]'
                    embedding_str = str(embedding_list)
                    
                    meta_dict = {
                        "source": item["source_file"],
                        "extracted_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    meta_json = json.dumps(meta_dict).replace("'", "''")
                    
                    sql = f"INSERT INTO tennis_rules (source_file, rule_id, content, metadata, embedding) VALUES ('{source_esc}', '{rule_id_esc}', '{content_esc}', '{meta_json}'::jsonb, '{embedding_str}'::vector);\n"
                    f.write(sql)
                    f.flush() # Ensure it's saved even if interrupted
                    
                    # Small wait to avoid hitting rate limits too fast (Free tier: 15 RPM)
                    time.sleep(1.0) 
                    
                except Exception as e:
                    print(f"SQL formulation error for {item.get('rule_id', 'unknown')}: {e}")

if __name__ == "__main__":
    etl = SQLGenFromText()
    try:
        text = etl.load_text("full_rules_text_en.txt")
        print(f"Loaded {len(text)} chars from text file.")
        
        chunks = etl.split_into_chunks(text, "2026-rules-of-tennis-english.pdf")
        print(f"Found {len(chunks)} chunks.")
        
        # Save to insert_rules_en.sql
        etl.generate_sql(chunks, "insert_rules_en.sql")
        print("Done! SQL saved to insert_rules_en.sql")
        
    except Exception as e:
        print(f"Fatal Error: {e}")
