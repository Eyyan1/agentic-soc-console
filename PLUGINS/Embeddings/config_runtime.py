import os


EMBEDDINGS_TYPE = os.getenv("EMBEDDINGS_TYPE", "openai")
EMBEDDINGS_API_KEY = os.getenv("EMBEDDINGS_API_KEY", os.getenv("OPENAI_API_KEY", "sk-local-placeholder"))
EMBEDDINGS_BASE_URL = os.getenv("EMBEDDINGS_BASE_URL", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small")
EMBEDDINGS_PROXY = os.getenv("EMBEDDINGS_PROXY", "")
EMBEDDINGS_SIZE = int(os.getenv("EMBEDDINGS_SIZE", "1536"))
