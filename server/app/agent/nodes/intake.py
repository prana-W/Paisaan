from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import interrupt
from app.agent.state import Profile
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _intake_fields() -> dict[str, str]:
    return {
        name: field.description
        for name, field in Profile.model_fields.items()
        if (field.json_schema_extra or {}).get("intake_required")
    }


def _get_llm(structured: bool = False, output_schema=None):
    settings = get_settings()
    llm = ChatGoogleGenerativeAI(
        model=settings.google_llm_model,
        google_api_key=settings.google_api_key,
        temperature=0.7,
    )
    if structured and output_schema:
        return llm.with_structured_output(output_schema)
    return llm


def _profile_is_complete(profile: dict) -> bool:
    return all(profile.get(f) is not None for f in _intake_fields())


def _generate_question(profile: dict, messages: list) -> str:
    fields = _intake_fields()
    filled = [f"  {desc}: {profile[name]}" for name, desc in fields.items() if profile.get(name) is not None]
    missing = [f"  {desc}" for name, desc in fields.items() if profile.get(name) is None]

    history = "\n".join(
        f"{'Assistant' if m.get('role') == 'assistant' else 'User'}: {m.get('content', '')}"
        for m in messages[-6:]
    ) or "(start of conversation)"

    system = SystemMessage(content=(
        "You are Paisaan, a friendly personal investment advisor in India. "
        "Gather the user's financial information through natural, fluid conversation.\n"
        "Guidelines:\n"
        "1. Be warm, concise, and professional. Use ₹ for monetary amounts.\n"
        "2. You can ask for multiple missing fields at once (e.g. 3-4 fields) to keep the flow fast and efficient.\n"
        "3. Look closely at the 'Recent conversation' and compare it with the 'Gathered' list:\n"
        "   - If the user tried to answer a field but the answer was ambiguous, incomplete, or couldn't be extracted, ask a gentle clarifying question for that specific field (e.g., 'You mentioned your savings are \"some\", could you give me an approximate number?').\n"
        "   - Otherwise, invite the user to share the remaining missing fields in a friendly, consolidated response."
    ))
    human = HumanMessage(content=(
        f"Gathered (already extracted successfully):\n{chr(10).join(filled) or '  (none yet)'}\n\n"
        f"Still needed:\n{chr(10).join(missing)}\n\n"
        f"Recent conversation:\n{history}\n\n"
        "Generate your next response to the user. Ask clarifying questions if there is ambiguity in recent messages, "
        "otherwise ask for the remaining missing fields in a conversational way. Return only the response text."
    ))

    response = _get_llm().invoke([system, human])
    content = response.content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part.get("text", ""))
        content = "".join(text_parts)
    return content.strip()


def _extract_profile_update(question: str, answer: str, current_profile: dict) -> dict:
    system = SystemMessage(content=(
        "Extract financial profile fields from the user's response. "
        "Convert shorthand amounts (e.g. '5k'→5000, '2 lakhs'→200000). "
        "Map risk: conservative→low, moderate→medium, aggressive→high. "
        "Only include fields clearly present in the response."
    ))
    human = HumanMessage(content=(
        f"Question: \"{question}\"\n"
        f"User response: \"{answer}\"\n"
        f"Current profile: {current_profile}\n\n"
        "Extract and return updated profile fields."
    ))

    update: Profile = _get_llm(structured=True, output_schema=Profile).invoke([system, human])
    return update.model_dump(exclude_none=True, exclude={"intake_complete", "questions_asked"})


def intake_node(state: dict) -> dict:
    profile = dict(state.get("profile", {}))
    messages = list(state.get("messages", []))

    if _profile_is_complete(profile):
        profile["intake_complete"] = True
        logger.info("Intake complete for thread_id=%s", state.get("thread_id"))
        # No completion message here — the consent node will speak next
        return {**state, "profile": profile, "messages": messages}

    question = _generate_question(profile, messages)
    logger.debug("Question generated for thread=%s: %s", state.get("thread_id"), question)

    answer = interrupt({"type": "question", "text": question})

    update = _extract_profile_update(question, str(answer), profile)
    logger.debug("Profile update: %s", update)

    for key, val in update.items():
        if key == "risk_signals":
            existing = profile.get("risk_signals", [])
            profile["risk_signals"] = existing + [v for v in val if v not in existing]
        else:
            profile[key] = val

    return {
        **state,
        "profile": profile,
        "messages": messages + [
            {"role": "assistant", "content": question},
            {"role": "user", "content": str(answer)},
        ],
    }
