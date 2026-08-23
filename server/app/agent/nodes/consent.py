from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import interrupt
from pydantic import BaseModel, Field
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConsentResult(BaseModel):
    consent: bool = Field(description="True if the user agreed/consented, False otherwise.")


def _get_llm(structured: bool = False, output_schema=None):
    settings = get_settings()
    llm = ChatGoogleGenerativeAI(
        model=settings.google_llm_model,
        google_api_key=settings.google_api_key,
        temperature=0.0,
    )
    if structured and output_schema:
        return llm.with_structured_output(output_schema)
    return llm


def ask_research_consent_node(state: dict) -> dict:
    """
    Checks if consent has been gathered. If not, asks the user.
    """
    messages = list(state.get("messages", []))
    
    # Generate the question
    question = (
        "I've got a great picture of your financial profile and preferences! "
        "Shall I proceed with scanning the live markets to fetch relevant data for you?"
    )
    
    # Use interrupt to pause the graph and ask the user
    answer = interrupt({"type": "question", "text": question})
    
    return {
        **state,
        "messages": messages + [
            {"role": "assistant", "content": question},
            {"role": "user", "content": str(answer)},
        ],
    }


def parse_research_consent_node(state: dict) -> dict:
    """
    Parses the user's answer from the interrupted state to determine if consent was given.
    """
    messages = state.get("messages", [])
    
    # The last message is the user's answer
    user_answer = messages[-1]["content"] if messages else ""
    
    system = SystemMessage(content=(
        "Determine if the user's response indicates consent to proceed. "
        "Responses like 'yes', 'yep', 'go for it', 'sure', 'yeah' should be True. "
        "Responses like 'no', 'stop', 'wait' should be False."
    ))
    human = HumanMessage(content=f"User response: '{user_answer}'")
    
    llm = _get_llm(structured=True, output_schema=ConsentResult)
    result = llm.invoke([system, human])
    
    logger.info(f"Parsed research consent as: {result.consent} from answer: '{user_answer}'")
    
    return {
        **state,
        "research_consent": result.consent
    }
