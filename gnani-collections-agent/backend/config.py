import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = PROJECT_DIR / "data"

# Load .env from project directory or backend directory
load_dotenv(PROJECT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "Gnani BFSI Collections Voice Agent"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Port & Host
    PORT: int = int(os.getenv("PORT", 8000))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GNANI_API_KEY: str = os.getenv("GNANI_API_KEY", "")
    
    # Gnani Enterprise Stack Endpoints
    GNANI_PRISMA_ENDPOINT: str = os.getenv("GNANI_PRISMA_ENDPOINT", "https://api.gnani.ai/asr/v3")
    GNANI_TIMBRE_ENDPOINT: str = os.getenv("GNANI_TIMBRE_ENDPOINT", "https://api.gnani.ai/tts/v3")
    GNANI_EVON_ENDPOINT: str = os.getenv("GNANI_EVON_ENDPOINT", "https://api.gnani.ai/llm/v3")

    # Primary Gemini Models
    GEMINI_STT_MODEL: str = "gemini-2.5-flash"
    GEMINI_BRAIN_MODEL: str = "gemini-2.5-flash"
    GEMINI_ESCALATION_MODEL: str = "gemini-2.5-flash"

    # Audio & Streaming Specs
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    BYTES_PER_SAMPLE: int = 2  # 16-bit PCM
    VAD_FRAME_SIZE_MS: int = 30  # 30ms frames
    BARGE_IN_THRESHOLD_MS: int = 300

    # Data Files
    BORROWER_PROFILES_PATH: Path = DATA_DIR / "borrower_profiles.json"
    DEMO_SCRIPTS_PATH: Path = DATA_DIR / "demo_scripts.json"

settings = Settings()

