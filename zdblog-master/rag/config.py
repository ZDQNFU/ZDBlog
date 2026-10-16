"""Environment defaults shared by production and isolated PostgreSQL tests."""
import os
from pathlib import Path

VECTOR_DIMENSIONS = 512  # bge-small-zh-v1.5; a dimension change requires a migration.
RAG_ENABLED = os.getenv('RAG_ENABLED', 'true').lower() in ('true', '1', 'yes')
RAG_EMBED_BASE_URL = os.getenv('RAG_EMBED_BASE_URL', '')
RAG_EMBED_API_KEY = os.getenv('RAG_EMBED_API_KEY', '')
RAG_EMBED_MODEL = os.getenv('RAG_EMBED_MODEL', os.getenv('BGE_EMBEDDING_MODEL', 'BAAI/bge-small-zh-v1.5'))
RAG_EMBED_DIM = int(os.getenv('RAG_EMBED_DIM', '512'))
RAG_LOCAL_MODEL_PATH = os.getenv('RAG_LOCAL_MODEL_PATH', os.getenv('BGE_MODEL_PATH', ''))
if RAG_LOCAL_MODEL_PATH and not Path(RAG_LOCAL_MODEL_PATH).is_absolute():
    RAG_LOCAL_MODEL_PATH = str((Path(__file__).resolve().parents[1] / RAG_LOCAL_MODEL_PATH).resolve())
RAG_EMBED_PROVIDER = os.getenv('RAG_EMBED_PROVIDER', 'local' if RAG_LOCAL_MODEL_PATH else 'openai')
RAG_LOCAL_DEVICE = os.getenv('RAG_LOCAL_DEVICE', os.getenv('EMBEDDING_DEVICE', 'cpu'))
RAG_LOCAL_PYTHON = os.getenv('RAG_LOCAL_PYTHON', '')
RAG_QUERY_INSTRUCTION = os.getenv('RAG_QUERY_INSTRUCTION', '为这个句子生成表示以用于检索相关文章：')
RAG_EMBED_SEND_DIMENSIONS = os.getenv('RAG_EMBED_SEND_DIMENSIONS', 'false').lower() == 'true'
RAG_CHUNK_SIZE = int(os.getenv('RAG_CHUNK_SIZE', '400'))
RAG_CHUNK_OVERLAP = int(os.getenv('RAG_CHUNK_OVERLAP', '60'))
RAG_MIN_CHUNK_CHARS = int(os.getenv('RAG_MIN_CHUNK_CHARS', '30'))
RAG_TOP_K = int(os.getenv('RAG_TOP_K', '5'))
RAG_CANDIDATE_K = int(os.getenv('RAG_CANDIDATE_K', '20'))
RAG_SNIPPET_CHARS = int(os.getenv('RAG_SNIPPET_CHARS', '300'))
RAG_MIN_DENSE_SCORE = float(os.getenv('RAG_MIN_DENSE_SCORE', '0.56'))
RAG_MIN_LEXICAL_SCORE = float(os.getenv('RAG_MIN_LEXICAL_SCORE', '0.45'))
RAG_TOOL_MAX_CHARS = 1500
