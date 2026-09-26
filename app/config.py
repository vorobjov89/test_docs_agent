import os

from dotenv import load_dotenv


load_dotenv()


# LLM_MODEL = os.getenv(
# "LLM_MODEL",
# "gpt-4.1-mini",
# )

YANDEX_API_KEY = os.getenv(
    "YANDEX_API_KEY"
)

YANDEX_FOLDER_ID = os.getenv(
    "YANDEX_FOLDER_ID"
)

BASE_URL = os.getenv(
    "BASE_URL"
)

MODEL_URI = os.getenv(
    "MODEL_URI"
)
