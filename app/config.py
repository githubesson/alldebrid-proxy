import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings:
    def __init__(self):
        self.ALLDEBRID_USERNAME = os.getenv("ALLDEBRID_USERNAME")
        self.ALLDEBRID_PASSWORD = os.getenv("ALLDEBRID_PASSWORD")
        self.ALLDEBRID_API_KEY = os.getenv("ALLDEBRID_APIKEY")

        self.API_TOKEN = os.getenv("API_TOKEN", "your-secret-token-here")

        self.HOST = os.getenv("HOST", "0.0.0.0")
        self.PORT = int(os.getenv("PORT", "8000"))
        self.RELOAD = os.getenv("RELOAD", "true").lower() == "true"

        self.CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "8192"))
        self.MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

settings = Settings() 