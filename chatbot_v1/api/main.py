from fastapi import APIRouter
import logging
import sys
from uvicorn.logging import DefaultFormatter
import os

# Define ANSI color codes for log levels
class ColorFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',   # Green
        'WARNING': '\033[33m', # Yellow
        'ERROR': '\033[31m',   # Red
        'CRITICAL': '\033[41m\033[37m', # White on Red background
        'TOOL': '\033[95m',    # Purple for tool calls
        'RESET': '\033[0m'     # Reset color
    }
    
    def format(self, record):
        # Save original levelname
        original_levelname = record.levelname
        
        # Add levelprefix if it doesn't exist
        if not hasattr(record, 'levelprefix'):
            record.levelprefix = self.get_level_prefix(record.levelname)
        
        # Check if this is a tool call log (special marker in the message)
        is_tool_call = False
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            if record.msg.startswith('TOOL:') or 'TOOL:' in record.msg:
                is_tool_call = True
        
        # Apply color based on level or tool call
        if is_tool_call:
            color = self.COLORS.get('TOOL')
            # Highlight the tool name in the message
            if hasattr(record, 'msg') and isinstance(record.msg, str):
                record.msg = record.msg.replace('TOOL:', f'{color}TOOL:{self.COLORS["RESET"]}')
        else:
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            # Add color to the level name
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
            # Also color the levelprefix
            if hasattr(record, 'levelprefix'):
                record.levelprefix = f"{color}{record.levelprefix}{self.COLORS['RESET']}"
        
        # Format the record
        try:
            result = super().format(record)
        except (KeyError, ValueError) as e:
            # Fallback to a simpler format if there's an error
            old_fmt = self._style._fmt
            self._style._fmt = "%(levelname)s: %(message)s"
            result = super().format(record)
            self._style._fmt = old_fmt
        
        # Restore original levelname
        record.levelname = original_levelname
        
        return result
    
    def get_level_prefix(self, levelname):
        """Generate a level prefix similar to uvicorn's DefaultFormatter"""
        if levelname == 'DEBUG':
            return 'DEBUG:'
        elif levelname == 'INFO':
            return 'INFO:'
        elif levelname == 'WARNING':
            return 'WARNING:'
        elif levelname == 'ERROR':
            return 'ERROR:'
        elif levelname == 'CRITICAL':
            return 'CRITICAL:'
        return ''

# Configure the root logger with custom formatter
handler = logging.StreamHandler(sys.stdout)
formatter = ColorFormatter("%(levelname)s: %(message)s")
handler.setFormatter(formatter)

# Force color output
os.environ["FORCE_COLOR"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"

# Set logging level
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    handlers=[handler]
)

logger = logging.getLogger()
logger.handlers = [handler]
logger.setLevel(logging.INFO)  # Changed from DEBUG to INFO to reduce unnecessary logs

from app.api.routes import chat, new

api_router = APIRouter()
api_router.include_router(chat.router)
api_router.include_router(new.router)
