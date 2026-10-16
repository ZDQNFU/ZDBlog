import hashlib
import math
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from .config import VECTOR_DIMENSIONS


def embedding_configured():
    if settings.RAG_EMBED_PROVIDER == 'local':
        return bool(settings.RAG_LOCAL_MODEL_PATH)
    return bool(settings.RAG_EMBED_BASE_URL and settings.RAG_EMBED_API_KEY)


def fingerprint():
    value = f'{settings.RAG_EMBED_PROVIDER}\n{settings.RAG_LOCAL_MODEL_PATH}\n{settings.RAG_EMBED_BASE_URL.rstrip("/")}\n{settings.RAG_EMBED_MODEL}\n{settings.RAG_EMBED_DIM}\n{settings.RAG_QUERY_INSTRUCTION}'
    return hashlib.sha256(value.encode()).hexdigest()


def validate_vector(vector):
    values = [float(v) for v in vector]
    if len(values) != VECTOR_DIMENSIONS or not all(math.isfinite(v) for v in values) or not any(values):
        raise ValueError('Embedding must be a finite, nonzero 512-dimensional vector')
    return values


def get_embedder():
    if settings.RAG_EMBED_DIM != VECTOR_DIMENSIONS:
        raise ImproperlyConfigured('RAG_EMBED_DIM does not match vector(512); migrate the schema first')
    if settings.RAG_EMBED_PROVIDER == 'local':
        from .local_embeddings import get_local_embedder
        return get_local_embedder(settings.RAG_LOCAL_MODEL_PATH, settings.RAG_LOCAL_DEVICE, settings.RAG_LOCAL_PYTHON)
    if settings.RAG_EMBED_PROVIDER != 'openai':
        raise ImproperlyConfigured('RAG_EMBED_PROVIDER must be local or openai')
    from langchain_openai import OpenAIEmbeddings
    if not embedding_configured():
        raise ImproperlyConfigured('Configure RAG_EMBED_BASE_URL and RAG_EMBED_API_KEY')
    kwargs = {'dimensions': VECTOR_DIMENSIONS} if settings.RAG_EMBED_SEND_DIMENSIONS else {}
    return OpenAIEmbeddings(model=settings.RAG_EMBED_MODEL, base_url=settings.RAG_EMBED_BASE_URL,
                           api_key=settings.RAG_EMBED_API_KEY, check_embedding_ctx_length=False,
                           chunk_size=32, request_timeout=15, max_retries=1, **kwargs)


def embed_documents(texts):
    texts = list(texts)
    vectors = get_embedder().embed_documents(texts)
    if len(vectors) != len(texts):
        raise ValueError('Embedding response count does not match input count')
    return [validate_vector(v) for v in vectors]


def embed_query(text):
    if settings.RAG_EMBED_PROVIDER == 'local':
        text = settings.RAG_QUERY_INSTRUCTION + text
    return validate_vector(get_embedder().embed_query(text))
