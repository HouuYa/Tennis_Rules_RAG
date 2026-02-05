import os
import re
import pdfplumber
import google.generativeai as genai
import numpy as np
import json
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

class SQLGenETL:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.gemini_key)
        self.embedding_model = "models/gemini-embedding-001"
        self.embedding_dim = 768
        # Improved regex to handle sparse text and various header formats
        self.split_pattern = re.compile(r"(\n\s*(?:규\s*칙|Rule|제|부\s*록|Appendix|Section|APPENDIX)\s*\d+.*?(?:\n|$))", flags=re.IGNORECASE)

    def extract_text(self, pdf_path):
        full_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    # Clean up excessive whitespace often found in PDFs
                    text = re.sub(r' +', ' ', text)
                    full_text.append(text)
        return "\n".join(full_text)

    def chunk_text(self, raw_text, source_name):
        parts = self.split_pattern.split(raw_text)
        chunks = []
        
        if parts[0].strip():
            intro_text = parts[0].strip()
            chunks.append({
                "source_file": source_name,
                "rule_id": "Introduction",
                "content": f"[테니스 규칙 서론]\n{intro_text}"
            })

        for i in range(1, len(parts), 2):
            header = re.sub(r"\s+", " ", parts[i].strip())
            content = parts[i+1].strip() if (i+1) < len(parts) else ""
            if not content: continue
            
            enhanced_content = f"출처: {source_name} > {header}\n내용: {content}"
            chunks.append({
                "source_file": source_name,
                "rule_id": header,
                "content": enhanced_content
            })
        return chunks

    def generate_sql(self, chunks, output_file):
        with open(output_file, "w", encoding="utf-8") as f:
            for item in tqdm(chunks, desc="Generating Embeddings"):
                try:
                    result = genai.embed_content(
                        model=self.embedding_model,
                        content=item["content"],
                        task_type="retrieval_document",
                        output_dimensionality=self.embedding_dim,
                    )
                    embedding = result['embedding']
                    
                    # Normalize
                    vec_np = np.array(embedding, dtype=float)
                    norm = np.linalg.norm(vec_np)
                    if norm > 0:
                        vec_np = vec_np / norm
                    embedding_list = vec_np.tolist()
                    
                    content_escaped = item["content"].replace("'", "''")
                    source_escaped = item["source_file"].replace("'", "''")
                    rule_escaped = item["rule_id"].replace("'", "''")
                    
                    sql = f"INSERT INTO tennis_rules (source_file, rule_id, content, embedding) VALUES ('{source_escaped}', '{rule_escaped}', '{content_escaped}', '{embedding_list}'::vector);\n"
                    f.write(sql)
                except Exception as e:
                    print(f"Error on {item['rule_id']}: {e}")

if __name__ == "__main__":
    etl = SQLGenETL()
    pdf_path = "./테니스규정집(2020.11.20 개정판).pdf"
    raw_text = etl.extract_text(pdf_path)
    chunks = etl.chunk_text(raw_text, "테니스규정집(2020.11.20 개정판).pdf")
    etl.generate_sql(chunks, "insert_rules.sql")
