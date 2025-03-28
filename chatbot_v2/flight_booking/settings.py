from dotenv import load_dotenv
from langchain._api import LangChainDeprecationWarning
import warnings
from llm_manager import LLMManager, LLMConfig

warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
load_dotenv()
llm_config = LLMConfig(
    provider="azure", model="gpt-4o-mini", config={"temperature": 0.1}
)
intent_llm_config = LLMConfig(
    provider="azure", model="gpt-4o", config={"temperature": 0}
)
llm = LLMManager.get_llm(llm_config)
intent_llm = LLMManager.get_llm(intent_llm_config)
