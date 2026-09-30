import os

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv(
    "API_KEY"
)
if API_KEY is None:
    raise ValueError("Переменная окружения API_KEY обязательна")

BASE_URL = os.getenv(
    "BASE_URL"
)
if BASE_URL is None:
    raise ValueError("Переменная окружения BASE_URL обязательна")

MODEL = os.getenv(
    "MODEL"
)
if MODEL is None:
    raise ValueError("Переменная окружения MODEL обязательна")

FOLDER_ID = os.getenv(
    "FOLDER_ID"
)
if FOLDER_ID == "":
    FOLDER_ID = None
