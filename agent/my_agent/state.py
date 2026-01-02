# state.py
import operator
from typing import TypedDict, Annotated, List, Optional, Literal, Any, Union, Dict
from langgraph.graph.message import add_messages, AnyMessage
from langchain.agents import AgentState as BaseAgentState
# --- Sub-Schemas ---

class QuestionObj(TypedDict):
    """Represents a static question definition loaded from the JSON form."""
    questionKey: str
    questionText: str
    questionType: str
    options: Union[List[str], Dict, None]  # Can be a list of choices or a dict of rules (min/max)
    validationRule: str

def merge_responses(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merges new response entries into the existing dictionary.
    New keys overwrite old keys (Upsert logic).
    """
    if not old_data:
        return new_data
    return {**old_data, **new_data}

class ResponseObj(TypedDict):
    """Represents the live status of a single question in the session."""
    questionKey: str
    value: Optional[Any]  # The actual answer (int, str, list)
    status: Literal["ASKED","UNASKED", "ANSWERED", "SKIPPED"]

# --- Main Agent State ---

class AgentState(BaseAgentState):
    """
    The short-term memory of the Agent. 
    Passed between all nodes in the Graph.
    """
    # 1. Base LangGraph History (Append-Only)
    messages: Annotated[List[AnyMessage], add_messages]

    # 2. Session Metadata (Injected Context)
    session_id: str
    form_id: str
    session_state: Literal["ONGOING", "FINISHED", "TERMINATED"]
    persona: str  # The personality loaded from the form

    # 3. Memory & Context
    questions: List[QuestionObj]     # All possible questions (ReadOnly after load)
    # responses: List[ResponseObj]     # The tracker for what has been answered
    responses: Annotated[Dict[str, ResponseObj], merge_responses]
    
    # 4. Flow Control (The "Pointer")
    current_question_key: Optional[str]  # Which question are we talking about right now?
    current_question_status: Literal["ASKED","CLARIFYING"]  # Removed IDLE 
    # consecutive_flags: int           # Frustration counter (increments on errors) # NOW MANAGED BY FrustrationGuardMiddleware