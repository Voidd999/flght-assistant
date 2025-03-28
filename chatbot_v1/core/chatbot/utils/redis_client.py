"""Redis client utilities for caching data."""

import os
import json
from redis import Redis
from typing import Any, Optional, Dict
from redis.exceptions import ConnectionError

# Redis client will be initialized on first use
REDIS_CLIENT = None

def get_redis_client() -> Redis:
    global REDIS_CLIENT
    if not REDIS_CLIENT or not check_connection():
        REDIS_CLIENT = Redis(
            host=os.getenv("REDIS_HOST"),
            port=int(os.getenv("REDIS_PORT")),
            password=os.getenv("REDIS_PASSWORD"),
            ssl=os.getenv("REDIS_SSL", "false") == "true",
            socket_keepalive=True,
            socket_timeout=10,
            retry_on_timeout=True,
            max_connections=50,
            health_check_interval=30
        )

        check_connection()
        print("Redis client initialized successfully")
    return REDIS_CLIENT

def check_connection() -> bool:
    try:
        if not REDIS_CLIENT:
            raise ConnectionError("Redis client not initialized")
        REDIS_CLIENT.ping()
        return True
    except ConnectionError:
        return False

in_memory_cache: Dict[str, Any] = {}

def init_redis_client() -> Optional[Redis] | Dict[str, Any]:
    """Lazy initialization of Redis client with error handling"""
    global REDIS_CLIENT
    if REDIS_CLIENT is None:
        try:
            REDIS_CLIENT = get_redis_client()
        except Exception as e:
            print(f"Redis connection failed. Error: {str(e)}")
            REDIS_CLIENT = in_memory_cache
    return REDIS_CLIENT

def load_json_to_redis(key: str, json_path: str) -> None:
    """Load JSON file into Redis or in-memory cache."""
    try:
        exists = REDIS_CLIENT.exists(key)
        if not exists:
            with open(json_path, 'r') as f:
                data = json.load(f)
            REDIS_CLIENT.set(key, json.dumps(data))
            return
    except Exception as e:
        # print(f"Redis operation failed, using in-memory cache. Error: {str(e)}")
        pass
    
    # Fallback to in-memory cache
    with open(json_path, 'r') as f:
        data = json.load(f)
    in_memory_cache[key] = data

def get_json_from_redis(key: str) -> Optional[dict]:
    """Get JSON data from Redis or in-memory cache."""
    try:
        if REDIS_CLIENT is not None:
            data = REDIS_CLIENT.get(key)
            return json.loads(data) if data else None
    except Exception as e:
        # print(f"Redis operation failed, using in-memory cache. Error: {str(e)}")
        pass
    
    return in_memory_cache.get(key)

# Constants for Redis keys
LANGUAGES_KEY = "flynas:languages"
AIRPORTS_KEY = "flynas:airports"

def get_language_config() -> Dict:
    """Get language configuration, initializing if necessary."""
    config = get_json_from_redis(LANGUAGES_KEY)
    if not config:
        init_static_data()
        config = get_json_from_redis(LANGUAGES_KEY)
        if not config:
            raise RuntimeError("Failed to load language configuration")
    return config

# Initialize function to load static data
def init_static_data():
    """Initialize static data in Redis."""
    base_path = "app/core/chatbot/kbs/static"
    load_json_to_redis(LANGUAGES_KEY, f"{base_path}/languages.json")
    load_json_to_redis(AIRPORTS_KEY, f"{base_path}/airports.json")
