from pydantic_settings import BaseSettings
import os
import platform
import sys


def _detect_edge_paths():
    """Auto-detect Edge User Data directory and available profiles."""
    system = platform.system()

    if system == "Windows":
        localappdata = os.environ.get("LOCALAPPDATA", "")
        user_data = os.path.join(localappdata, "Microsoft", "Edge", "User Data") if localappdata else ""
    elif system == "Darwin":
        user_data = os.path.expanduser("~/Library/Application Support/Microsoft Edge/User Data")
    elif system == "Linux":
        user_data = os.path.expanduser("~/.config/microsoft-edge")
    else:
        user_data = ""

    # Detect available profile directories — prefer the one with Extensions AND most recent activity
    profile_dir = "Default"
    best_mtime = 0
    if user_data and os.path.isdir(user_data):
        for name in os.listdir(user_data):
            full = os.path.join(user_data, name)
            if os.path.isdir(full) and os.path.exists(os.path.join(full, "Preferences")):
                has_ext = os.path.isdir(os.path.join(full, "Extensions"))
                mtime = os.path.getmtime(os.path.join(full, "Preferences"))
                # Score: Extensions=True beats False, then newer mtime wins
                score = (int(has_ext), mtime)
                if score > (int(best_mtime > 0 or not has_ext), best_mtime):
                    profile_dir = name
                    best_mtime = mtime

    return user_data, profile_dir


def _is_persistent_context_available():
    """Check if persistent_context is usable."""
    if platform.system() == "Linux":
        # Check if running in Docker (no GUI)
        if os.path.exists("/.dockerenv"):
            return False
        # Check if DISPLAY is set (headless X server)
        if not os.environ.get("DISPLAY"):
            return False
    return True


EDGE_USER_DATA, EDGE_PROFILE_DIR = _detect_edge_paths()
PERSISTENT_CONTEXT_AVAILABLE = _is_persistent_context_available()
IS_DOCKER = os.path.exists("/.dockerenv")


class Settings(BaseSettings):
    # Edge browser settings (auto-detected, can be overridden via env)
    edge_user_data: str = EDGE_USER_DATA
    edge_profile_dir: str = EDGE_PROFILE_DIR
    persistent_context_available: bool = PERSISTENT_CONTEXT_AVAILABLE

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
    yiwugo_cookie: str = ""
    buyin_cookie: str = ""

    own_platform_db_url: str = ""
    own_platform_api_key: str = ""

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8001

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Print detected environment on startup (to stderr — won't contaminate subprocess stdout)
if not PERSISTENT_CONTEXT_AVAILABLE:
    print(f"[config] Server mode — persistent_context unavailable", file=sys.stderr)
else:
    print(f"[config] Edge: {settings.edge_user_data} | Profile: {settings.edge_profile_dir}", file=sys.stderr)