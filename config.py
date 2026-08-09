import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-for-any-real-deployment")
    DEBUG = os.environ.get("FLASK_DEBUG", "True") == "True"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB upload cap for class data files
    DEFAULT_PASS_THRESHOLD = float(os.environ.get("DEFAULT_PASS_THRESHOLD", 50.0))
    DEFAULT_TARGET_CLASS_AVERAGE = float(
        os.environ.get("DEFAULT_TARGET_CLASS_AVERAGE", 60.0)
    )
