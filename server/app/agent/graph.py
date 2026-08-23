from langgraph.graph import StateGraph, START, END
from app.agent.subgraphs.intake_subgraph import build_intake_subgraph
from app.agent.subgraphs.market_subgraph import build_market_subgraph
from app.core.logging import get_logger
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import interrupt
from pydantic import BaseModel, Field
from app.core.config import get_settings

logger = get_logger(__name__)

_graph = None


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


def _check_consent(state: dict) -> str:
    """Conditional edge from parse_consent."""
    if state.get("research_consent") is True:
        return "market_subgraph"
    return END


def build_graph(checkpointer):
    builder = StateGraph(dict)

    # 1. Intake Subgraph
    intake_subgraph = build_intake_subgraph()
    builder.add_node("intake_subgraph", intake_subgraph)

    # 2. Consent Nodes
    builder.add_node("ask_research_consent", ask_research_consent_node)
    builder.add_node("parse_research_consent", parse_research_consent_node)

    # 3. Market Subgraph
    market_subgraph = build_market_subgraph()
    builder.add_node("market_subgraph", market_subgraph)

    # Wiring
    builder.add_edge(START, "intake_subgraph")
    
    # After intake finishes, ask for consent
    builder.add_edge("intake_subgraph", "ask_research_consent")
    
    # After user answers the interrupt, parse it
    builder.add_edge("ask_research_consent", "parse_research_consent")
    
    # If consent=True -> market_subgraph, else -> END
    builder.add_conditional_edges("parse_research_consent", _check_consent, {
        "market_subgraph": "market_subgraph",
        END: END
    })
    
    # After market research, end for now (Phase 4 will attach here)
    builder.add_edge("market_subgraph", END)

    compiled = builder.compile(checkpointer=checkpointer)
    print(compiled.get_graph().draw_mermaid())
    
    logger.info("Graph compiled (%d nodes)", len(builder.nodes))
    return compiled


def get_graph():
    if _graph is None:
        raise RuntimeError("Graph not initialised. Call init_graph() at app startup.")
    return _graph


def init_graph(checkpointer) -> None:
    global _graph
    _graph = build_graph(checkpointer)
    logger.info("Agent graph initialised")
