from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0

    # MiniMax (Primary LLM)
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimax.chat/v1"
    minimax_model: str = "MiniMax-M2.7-highspeed"

    # Volcengine (Doubao) - Optional, for multimodal later
    volc_access_key: str = ""
    volc_secret_key: str = ""
    doubao_endpoint: str = "https://ark.cn-beijing.volces.com/api/v3"
    doubao_model_id: str = "doubao-seed-2-0-pro"

    # DeepSeek - Optional, for deep reasoning later
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-v4-pro"

    # Cookies for web scraping
    chanmama_cookie: str = ""
    alibaba_1688_cookie: str = ""

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8001

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()