import os


REDIS_URL = os.getenv("REDIS_URL", "redis://:redis-stack-password-for-agentic-soc-platform@localhost:6379/")
REDIS_STREAM_MAX_LENGTH = int(os.getenv("REDIS_STREAM_MAX_LENGTH", "10000"))
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
