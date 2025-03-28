import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from redis import Redis
from app.api.main import api_router, ColorFormatter
from app.api.routes import chat  # Import the chat module containing chat_service
from app.core.chatbot.utils.redis_client import init_redis_client
from contextlib import asynccontextmanager
import logging
import sys

if os.getenv("ENVIRONMENT") != "production":
    env_path = Path(__file__).resolve().parent.parent / ".env"
    # print(env_path)
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv(override=True)

# Configure uvicorn logging to use our custom formatter
import uvicorn.logging

handler = logging.StreamHandler(sys.stdout)
formatter = ColorFormatter("%(levelname)s: %(message)s")
handler.setFormatter(formatter)

# Replace uvicorn's default handler with our custom handler
for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
    logger = logging.getLogger(logger_name)
    logger.handlers = [handler]

# Force color output
os.environ["FORCE_COLOR"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"

app = FastAPI(
    title=os.environ["PROJECT_NAME"],
    version=os.environ["VERSION"],
    openapi_url=f"{os.environ['API_V1_STR']}/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(api_router, prefix=os.environ["API_V1_STR"])

# Add a test log to verify colors are working
logger = logging.getLogger("fastapi")
logger.info("FastAPI application started with colored logging")
