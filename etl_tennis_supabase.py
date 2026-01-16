import os
import re
import time
import requests
import pdfplumber
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
import numpy as np
# note: supabase / google generative imports are done lazily in __init__

# 로깅 및 환경 설정
load_dotenv()
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TennisSupabaseETL:
    def __init__(self):
        # 1. 환경 변수 로드 및 클라이언트 설정
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        # 테스트용: DRY_RUN=1 로 설정하면 Supabase에 쓰지 않습니다.
        self.dry_run = os.getenv("DRY_RUN", "0") == "1"
        # 테스트용: SKIP_EMBEDDING=1 로 설정하면 Gemini 임베딩 호출을 생략하고 청크까지만 처리합니다.
        self.skip_embedding = os.getenv("SKIP_EMBEDDING", "0") == "1"
        # 테스트용: SKIP_REMOTE=1 로 설정하면 원격(http) 파일 다운로드를 건너뜁니다.
        self.skip_remote = os.getenv("SKIP_REMOTE", "0") == "1"

        # embedding 호출을 건너뛰는 테스트 모드이면 외부 키/클라이언트 초기화를 생략
        if not self.skip_embedding:
            if not all([self.supabase_url, self.supabase_key, self.gemini_key]):
                raise ValueError("❌ .env 파일에 필수 키(SUPABASE_URL, SUPABASE_SERVICE_KEY, GEMINI_API_KEY)가 누락되었습니다.")

            # Supabase 클라이언트 및 Gemini 구성은 실제 embedding/insert가 필요할 때만 수행
            try:
                from supabase import create_client, Client
                import google.generativeai as genai

                self.supabase_client_available = True
                self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
                genai.configure(api_key=self.gemini_key)
                self._genai = genai
            except Exception as e:
                # supabase client 설치 불가(빌드 문제 등) 시 REST 엔드포인트를 통한 대체 삽입 경로 준비
                logger.warning(f"supabase client 초기화 실패(fallback to REST): {e}")
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                self._genai = genai
                self.supabase_client_available = False
                self.supabase = None
                # REST 엔드포인트 (테이블명 직접 사용)
                self._rest_url = self.supabase_url.rstrip('/') + '/rest/v1/tennis_rules'
                self._rest_headers = {
                    'apikey': self.supabase_key,
                    'Authorization': f'Bearer {self.supabase_key}',
                    'Content-Type': 'application/json',
                    'Prefer': 'return=representation'
                }
        else:
            self.supabase = None
            self._genai = None

        # 모델 설정: Gemini 임베딩 모델 및 768차원으로 고정
        self.embedding_model = "models/gemini-embedding-001"
        self.embedding_dim = 768  # Supabase 테이블 vector(768)에 맞춤

        # 2. 조항 분할을 위한 정규식 (공백 유연 대응)
        # 영어: Rule 1, Article 1, Appendix I / 한글: 규칙 1, 제 1 조, 부록 I
        self.split_pattern = re.compile(r"(규\s*칙\s*\d+|Rule\s*\d+|Article\s*\d+|제\s*\d+\s*조|부\s*록\s*[IVX]+|APPENDIX\s*[IVX]+|Section\s*[A-Z])", flags=re.IGNORECASE)

    def download_file(self, url: str, save_dir: str = "./downloads") -> str:
        """URL에서 파일을 다운로드하거나 로컬 경로 반환"""
        if not url.startswith("http"):
            return url  # 로컬 파일 경로인 경우 그대로 반환

        Path(save_dir).mkdir(exist_ok=True)
        filename = url.split("/")[-1]
        if not filename.endswith(".pdf"):
            filename = "downloaded_rule.pdf"
        
        save_path = os.path.join(save_dir, filename)
        
        logger.info(f"📥 다운로드 시작: {url}")
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"✅ 다운로드 완료: {save_path}")
            return save_path
        else:
            raise Exception(f"파일 다운로드 실패: {response.status_code}")

    def extract_text(self, pdf_path: str) -> str:
        """pdfplumber를 사용하여 텍스트 추출 (표 구조 유지)"""
        logger.info(f"📖 텍스트 추출 중: {pdf_path}")
        full_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # layout=True: 표의 물리적 배치를 텍스트로 근사하게 표현
                text = page.extract_text(layout=True)
                if text:
                    full_text.append(text)
        return "\n".join(full_text)

    def chunk_text(self, raw_text: str, source_name: str) -> List[Dict[str, Any]]:
        """정규식 기반 조항 분할 및 검색 최적화(Prefixing)
        - 긴 조항은 적당한 길이로 분할하여 임베딩 API 제한을 피함
        """
        parts = self.split_pattern.split(raw_text)
        chunks = []

        # 서론 부분 처리
        if parts[0].strip():
            intro_text = parts[0].strip()
            chunks.append({
                "source_file": source_name,
                "rule_id": "Introduction",
                "content": f"[테니스 규칙 서론]\n{intro_text}",
                "original_content": intro_text
            })

        # 조항(Header) + 내용(Content) 쌍으로 처리
        for i in range(1, len(parts), 2):
            header = parts[i].strip()
            # 정규식으로 찾은 헤더 정제 (예: "규  칙 1" -> "규칙 1")
            clean_header = re.sub(r"\s+", " ", header)
            content = parts[i+1].strip() if (i+1) < len(parts) else ""

            if not content:
                continue

            # ✨ 검색 성능 최적화: Prefixing 적용
            enhanced_content = f"출처: {source_name} > {clean_header}\n내용: {content}"

            # 긴 내용은 2000자 단위로 쪼개기 (간단 분할, 필요시 토큰 기반 분할로 대체)
            max_len = 2000
            if len(enhanced_content) <= max_len:
                chunks.append({
                    "source_file": source_name,
                    "rule_id": clean_header,
                    "content": enhanced_content,
                    "original_content": content
                })
            else:
                # 근접 공백 위치에서 분할
                start = 0
                part_idx = 1
                while start < len(enhanced_content):
                    end = min(start + max_len, len(enhanced_content))
                    # 가능한 한 공백에서 잘라 읽기 좋게 만듦
                    if end < len(enhanced_content):
                        space_pos = enhanced_content.rfind(' ', start, end)
                        if space_pos > start:
                            end = space_pos
                    chunk_text = enhanced_content[start:end].strip()
                    chunks.append({
                        "source_file": source_name,
                        "rule_id": f"{clean_header} (Part {part_idx})",
                        "content": chunk_text,
                        "original_content": content
                    })
                    start = end
                    part_idx += 1

        logger.info(f"✂️  Chunking 완료: {len(chunks)}개 조항 생성")
        return chunks

    def generate_embeddings_and_upload(self, chunks: List[Dict[str, Any]]):
        # GEMINI API 키 기본값/플레이스홀더 체크
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key or 'your-google-gemini-api-key' in gemini_key.lower():
            logger.error("❌ GEMINI_API_KEY가 비어있거나 플레이스홀더로 보입니다. 임베딩을 진행할 수 없습니다.")
            self.gemini_issue = True
            return
        batch_size = 10
        total_chunks = len(chunks)

        logger.info(f"🚀 Supabase 업로드 시작 (총 {total_chunks}개, 배치 사이즈 {batch_size})")

        for i in range(0, total_chunks, batch_size):
            batch = chunks[i:i+batch_size]
            db_records = []

            for item in batch:
                try:
                    if self.skip_embedding:
                        logger.info(f"[SKIP_EMBEDDING] 임베딩 생성 스킵: {item.get('rule_id')}")
                        continue

                    # 1. Gemini API 호출
                    result = self._genai.embed_content(
                        model=self.embedding_model,
                        content=item["content"],
                        task_type="retrieval_document",
                        output_dimensionality=self.embedding_dim,
                    )

                    # 2. 임베딩 벡터 추출 (여러 반환 형식에 대응)
                    embedding_vector = None
                    if isinstance(result, dict):
                        if 'embedding' in result:
                            embedding_vector = result['embedding']
                        elif 'embeddings' in result and isinstance(result['embeddings'], list):
                            embedding_vector = result['embeddings'][0]
                        elif 'data' in result and isinstance(result['data'], list) and result['data']:
                            if 'embedding' in result['data'][0]:
                                embedding_vector = result['data'][0]['embedding']
                    elif hasattr(result, 'embedding'):
                        embedding_vector = getattr(result, 'embedding')
                    elif hasattr(result, 'embeddings'):
                        embeddings_attr = getattr(result, 'embeddings')
                        embedding_vector = embeddings_attr[0] if embeddings_attr else None

                    if embedding_vector is None:
                        raise ValueError("임베딩을 추출할 수 없습니다. 응답 포맷을 확인하세요.")

                    vec_np = np.array(embedding_vector, dtype=float)

                    # 차원 불일치 시 자르거나 0으로 패딩하여 고정 차원 유지
                    if vec_np.shape[0] != self.embedding_dim:
                        logger.warning(f"임베딩 차원 불일치: 기대={self.embedding_dim}, 실제={vec_np.shape[0]} - 자르거나 패딩합니다.")
                        if vec_np.shape[0] > self.embedding_dim:
                            vec_np = vec_np[:self.embedding_dim]
                        else:
                            pad = np.zeros(self.embedding_dim - vec_np.shape[0], dtype=float)
                            vec_np = np.concatenate([vec_np, pad])

                    # 정규화
                    norm = np.linalg.norm(vec_np)
                    if norm > 0:
                        normed_embedding = (vec_np / norm).astype(float).tolist()
                    else:
                        normed_embedding = vec_np.astype(float).tolist()

                    db_records.append({
                        "source_file": item["source_file"],
                        "rule_id": item["rule_id"],
                        "content": item["content"],
                        "metadata": {"original_len": len(item.get("original_content", ""))},
                        "embedding": normed_embedding
                    })

                    time.sleep(0.2) 

                except Exception as e:
                    logger.exception(f"❌ 임베딩 생성 실패 ({item.get('rule_id', 'unknown')}): {e}")

            # Supabase Insert (배치 단위)
            if db_records:
                if self.dry_run:
                    logger.info(f"[DRY_RUN] Batch {i//batch_size + 1} 준비 완료 ({len(db_records)}건) - DB 쓰기 스킵")
                else:
                    try:
                        if self.supabase_client_available:
                            res = self.supabase.table("tennis_rules").insert(db_records).execute()
                        else:
                            # REST API를 통한 삽입
                            for record in db_records:
                                # 레코드 단위로 POST 요청
                                response = requests.post(
                                    self._rest_url,
                                    headers=self._rest_headers,
                                    json=record
                                )
                                if response.status_code not in [200, 201]:
                                    logger.warning(f"REST API 삽입 실패: {response.status_code} - {response.text}")
                                else:
                                    logger.info(f"  - REST API를 통한 레코드 삽입 완료")

                        # supabase-py는 에러를 예외로 던지므로 도중 오류는 except로 처리됨
                        logger.info(f"  - Batch {i//batch_size + 1} 업로드 완료 ({len(db_records)}건)")
                    except Exception as e:
                        logger.exception(f"❌ Supabase Insert 실패: {e}")

    def run(self, target_list: List[Dict[str, str]]):
        """전체 파이프라인 실행"""
        logger.info("🔥 ETL 프로세스 시작")
        
        for target in target_list:
            try:
                # 1. 다운로드
                # 원격 다운로드를 건너뛰는 옵션이 있으면 http(s) URL은 스킵
                if self.skip_remote and str(target.get("url", "")).lower().startswith("http"):
                    logger.info(f"[SKIP_REMOTE] 원격 파일 다운로드 건너뜀: {target.get('url')}")
                    continue
                file_path = self.download_file(target["url"])
                filename = os.path.basename(file_path)

                if not os.path.exists(file_path):
                    logger.error(f"파일이 존재하지 않습니다: {file_path} - 스킵합니다.")
                    continue
                
                # 2. 텍스트 추출
                raw_text = self.extract_text(file_path)
                
                # 3. Chunking
                chunks = self.chunk_text(raw_text, filename)
                
                # 4. Embedding & Upload
                if chunks:
                    self.generate_embeddings_and_upload(chunks)
                else:
                    logger.warning(f"처리할 청크가 없습니다: {filename}")
                
                logger.info(f"✅ 파일 처리 완료: {filename}\n")
                
            except Exception as e:
                logger.exception(f"❌ 파일 처리 중 치명적 오류 발생 ({target.get('name', 'unknown')}): {e}")

        logger.info("🎉 모든 작업이 완료되었습니다.")

# --- 실행부 ---
if __name__ == "__main__":
    # 처리할 문서 리스트 (URL 또는 로컬 경로)
    target_docs = [
        {
            "name": "KTA_Rules_KR", 
            "url": "./테니스규정집(2020.11.20 개정판).pdf"  # 로컬 파일 이름으로 수정
        },
        {
            "name": "ITF_Rules_2025_EN", 
            "url": "https://www.itftennis.com/media/7221/2025-rules-of-tennis-english.pdf"
        },
        {
            "name": "ITF_Duties_Procedures",
            "url": "https://www.itftennis.com/media/2509/2025-duties-procedures-for-officials.pdf"
        }
    ]

    etl = TennisSupabaseETL()
    etl.run(target_docs)