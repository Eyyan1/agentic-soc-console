import os


LLM_CONFIGS = [
    {
        "type": os.getenv("LLM_TYPE", "openai"),
        "api_key": os.getenv("OPENAI_API_KEY", "sk-local-placeholder"),
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "proxy": os.getenv("OPENAI_PROXY") or None,
        "tags": ["cheap", "fast", "powerful", "function_calling", "structured_output"],
    }
]
