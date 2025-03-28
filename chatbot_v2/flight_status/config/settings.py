import os
from dotenv import load_dotenv
from langchain._api import LangChainDeprecationWarning
import warnings
from llm_manager import LLMManager, LLMConfig

warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
load_dotenv()
llm_config = LLMConfig(
    provider="azure", model="gpt-4o-mini", config={"temperature": 0.1}
)
llm = LLMManager.get_llm(llm_config)
DEPENDENCY_RULES = {
    "check_status_pnr": ["pnr"],
    "check_status_details": ["date", "origin", "destination"],
    "get_more_info": ["flight_status"],
    "ask_delay_reason": ["flight_status"],
}
