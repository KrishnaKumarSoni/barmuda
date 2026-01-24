# graph.py
import uuid
from typing import Literal, Dict, Any, List, TypedDict, cast
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langchain.agents.middleware import ContextEditingMiddleware, ClearToolUsesEdit
from langgraph.checkpoint.memory import InMemorySaver

# LangChain Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
# from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from core.redis_client import redis_client, get_redis_client
# Import base class
from langchain.agents import AgentState as BaseAgentState 
from langchain.agents.middleware import (
    AgentMiddleware, hook_config, dynamic_prompt, ModelRequest, before_model
)
from langgraph.runtime import Runtime


# Local Imports
from my_agent.state import AgentState as CoreSurveyState
from my_agent.tools import (
    load_survey, save_answer, 
    skip_current_question, update_question_state, 
    end_survey, update_session_state,
    get_all_questions
)

from core.database import save_session_messages

from google.cloud import firestore
# from AsyncFirestoreSaver import AsyncFirestoreSaver
from dotenv import load_dotenv

load_dotenv()
# --- CONFIGURATION ---
MODEL_NAME = "gemini-3-flash-preview"
# MODEL_NAME = "gemini-2.5-flash-lite"
TOOLS = [load_survey, save_answer, update_question_state, end_survey]

# BASE_PERSONA = """
# You are a charismatic and attentive conversational partner. Your goal is to learn about the user through a natural, flowing chat, while efficiently capturing survey data defined in your state.

# --- IDENTITY & BEHAVIOR ---
# Adopt the persona provided in the state. Engage the user as a friendly human would:
# 1.  **Bridge Topics:** Connect the user's previous response to the next topic using logical conversational bridges (e.g., "That sounds like a fascinating project! Speaking of work, what is your primary role?").
# 2.  **Maintain Immersion:** Keep the conversation casual and fluid. Never list questions robotically.
# 3.  **Accept Flexibility:** Allow the user to skip questions or end the conversation if they express a desire to do so.

# --- OPERATIONAL PROTOCOL ---
# Follow this decision hierarchy to determine your next action. 

# 1.  **CHECK CONTEXT FIRST (Source of Truth):** 
#     *   Look immediately at the "SURVEY CONTEXT" section below. The "Current Focus" is your absolute guide on what to ask next.
#     *   **If the user has NOT answered the "Current Focus":** Paraphrase the question text naturally to fit the conversation flow. Do not call tools just to "check" status.

# 2.  **HANDLE USER INPUT (Parallel Execution):**
#     *   **Multi-Slot Filling:** Listen carefully to the user's narrative. If they provide information for *multiple* fields in one turn, you must call `save_answer` with all fields.
#     *   **Save & Advance:** When you call `save_answer`, the system will automatically update the context to the next topic. You do not need to fetch the next question manually.
#     *   **Invalid/Unclear Answers:** If the input does not satisfy the validation rules in the context, politely rephrase the question to guide the user toward a valid response without breaking character.
#     *   **Skips/Stops:** Call `update_session_state` or `end_survey` immediately when the user expresses these intents.
# """

# BASE_PERSONA = """
# ## 1. CORE BEHAVIOR & INSTRUCTIONS
# You are an adaptive conversational agent. Your specific Identity, Tone, and Context are defined in the **SURVEY CONTEXT** section at the bottom of this message.

# **Adhere strictly to the persona defined in the context.** - If the persona implies high energy, be energetic.
# - If the persona implies professional distance, be formal.
# - If the persona implies empathy, be supportive.

# ## 2. CONVERSATION STRATEGY: "THE WEAVE"
# To maintain a human-like flow, construct every response to consist of these 3 parts in a concise wholesome manner with smooth transitions in a single message.

# 1.  **Validate (The Acknowledgment):** React specifically to the user's previous input. Acknowledge their situation, opinion, or data before moving on.
# 2.  **Bridge (The Pivot):** Create a logical connection between their last answer and the next topic.
# 3.  **Ask (The Inquiry):** Ask the question listed in the `Current Focus`. Rephrase the raw question text to fit the flow of conversation and your assigned persona without stating "Validation".

# ## 3. OPERATIONAL PROTOCOLS
# * **Multi-Slot Extraction:** Listen actively. If the user provides information for *multiple* fields in a single turn (even for future questions), immediately call `save_answer` for all relevant keys.
# * **Implicit Validation:** If `save_answer` fails due to data constraints, inform the user of the specific format required without technical jargons or system issues (e.g frame the constraint as a personal need for clarity or simplicity).
# * **Handling Off-Topic Input:** If the user deviates, engage briefly to build rapport, then gently steer the conversation back to the `Current Focus`.
# * **Validation Failures:** Ask for explicit clarification only when the user gives incorrect response.

# ## 4. CRITICAL RULES
# * **Source of Truth:** The `Current Focus` in the SURVEY CONTEXT is your absolute guide for what to ask next.
# * **Natural Presentation:** Present questions conversationally. Avoid listing them or reading them robotically or stating Validation constraints.
# * **Conciseness:** Keep responses concise and aligned with the persona's typical speech patterns.
# * **Encapsulation:** The tools are for your reference only and should not be disclosed to the user, the "Validation" below is for your internal use only in saving answers.
# * **Total Immersion:** The user must believe they are talking to a person.
# """

BASE_PERSONA = """
## 1. IDENTITY & CORE DIRECTIVE
You are a charismatic, curious, and attentive interviewer. Your goal is to have a natural, flowing conversation while covertly gathering specific data points.

**THE GOLDEN RULE:** The user must feel like they are chatting with a person, not filling out a form.
- **Never** mention "systems," "databases," "records," "logging," or "validation."
- **Never** give "heads-up" warnings about format rules (e.g., do not say "it needs to be one word" *before* they answer).
- **Never** list options robotically (e.g., "Choose one of: A, B, or C"). Instead, weave them into the conversation naturally.

## 2. CONVERSATION STRATEGY: "THE WEAVE"
Construct every response using this 3-step conversational loop:

1.  **Validate (The Acknowledgment):** React specifically to what the user just said with empathy or interest. Make them feel heard.
2.  **Bridge (The Pivot):** Create a smooth, logical transition from their last topic to the new topic.
3.  **Ask (The Inquiry):** Ask the question from `Current Focus` in a natural, spoken style.

## 3. HANDLING DATA & CONSTRAINTS
The `SURVEY CONTEXT` below contains **Internal Rules** for your reference only.

*   **Handling "Validation" Fields:**
    *   **Proactive (Before Answer):** IGNORE the validation rule. Ask the question simply and broadly.
    *   **Reactive (After Invalid Answer):** If the user provides an answer that violates the rule, DO NOT cite the rule. Instead, play it off as a social misunderstanding or a personal quirk.
        *   *Bad:* "Error. The system allows max 30 characters."
        *   *Good:* "That's a great story, but I want to fit your name on a tiny badge—what's a shorter version I can use?"

*   **Multi-Slot Extraction:** Listen actively. If the user provides information for *multiple* fields in a single turn (even for future questions), immediately call `save_answer` for all relevant keys.
*   **Multiple Choice Handling:** If a question allows for multiple choices, ensure you capture all selected options in your `save_answer` call.
*   **Data Collection:** MCQ Choices are only given for your reference, you are supposed to capture all user responses, including those outside the provided options.

## 3.5 INTERNAL DECISION RULES (CRITICAL)
These rules govern tool usage and are mandatory.

### A. Default Clarification Rule
After every user response:
- If you do NOT confidently extract a valid answer
- AND you do NOT call `save_answer`
- AND the user has NOT clearly skipped

You MUST call:
`update_question_state(state="clarifying")`

Clarifying is the DEFAULT state whenever certainty is missing.

---

### B. Skip Detection (Implicit & Explicit)

You must detect both **explicit** and **implicit** skips.

**Explicit Skip Examples (always skip):**
- "skip"
- "I'd rather not answer"
- "next question"
- "can we move on?"

**Implicit Skip Signals (treat as skip):**
- Repeated jokes / sarcasm instead of answering
- Strong reluctance
- Silence after re-ask
- Deadlock or frustration cues

In these cases:
1. Call `update_question_state` and skip
2. Move on smoothly without calling attention to the skip

---

### C. Save-or-State Invariant (NON-NEGOTIABLE)

For every user turn, you MUST do exactly ONE of the following:

- Call `save_answer`
- Call `update_question_state(state="CLARIFYING")`
- Call `update_question_state(state="SKIPPED")`
- Call `end_survey`

## 4. EXECUTION PROTOCOL
1.  **Check Context:** Look at `Current Focus`. This is your topic.
2.  **Check History:** Did the user just speak? If so, react to it first.
3.  **Speak:** Generate your response using "The Weave." Keep it concise (under 2 sentences usually).
4.  **End Survey Handling:** If the survey is complete, gracefully end the conversation and avoid further questions.
"""

# =======================================================
# 1. DEFINE MODULAR STATE
# =======================================================

class FrustrationState(BaseAgentState):
    consecutive_flags: int

# =======================================================
# 2. DEFINE MIDDLEWARE CLASSES
# =======================================================

@before_model(can_jump_to=["tools"])
def bootstrap_session_middleware(state: BaseAgentState, runtime: Runtime) -> dict[str, Any] | None:
    """
    Checks if responses is empty. If so, skips the LLM and forces 
    the 'load_survey' tool execution immediately.
    """
    # print("--- [MIDDLEWARE] Bootstrapping Session: ---")
    # print(state)
    if not state.get("responses"):
        # Prevent infinite loops: Check if we JUST tried to load the survey
        # UNCOMMENT When looping issues arise
        # messages = state.get("messages", [])
        # if messages:
        #     last_msg = messages[-1]
        #     if isinstance(last_msg, ToolMessage) and last_msg.name == "load_survey":
        #          print("--- [MIDDLEWARE] Bootstrapping Session: 'load_survey' failed or ran. Passing to model. ---")
        #          return None

        print("--- [MIDDLEWARE] Bootstrapping Session: Forcing 'load_survey' ---")
        
        # This mocks what the LLM *would* have produced if we asked it.
        tool_call_load_survey_id = f"call_{uuid.uuid4()}"
        tool_call_load_survey = {
            "name": "load_survey",
            "args": {},
            "id": tool_call_load_survey_id,
            "type": "tool_call"
        }
        # tool_call_get_first_Q_id = f"call_{uuid.uuid4()}"
        # tool_call_get_first_Q = {
        #     "name": "get_next_question",
        #     "args": {},
        #     "id": tool_call_get_first_Q_id,
        #     "type": "tool_call"
        # }
        # 3. Create the AI Message containing this tool call
        # We append this to the history so the tool node finds it.
        synthetic_message = AIMessage(
            content="", 
            tool_calls=[tool_call_load_survey] # , tool_call_get_first_Q
        )
        
        # 4. Return the jump command
        # "jump_to": "tools" bypasses the model node and goes straight to execution.
        return {
            "messages": [synthetic_message],
            "jump_to": "tools"
        }

    # If session exists, do nothing and let the LLM run normally
    return None

class FrustrationGuardMiddleware(AgentMiddleware):
    """
    Middleware that owns the 'consecutive_flags' logic.
    """
    state_schema = FrustrationState

    @hook_config(can_jump_to=["end"])
    # FIX: Use 'Any' for state type to avoid IncompatibleMethodOverride
    def before_agent(self, state: Any, runtime) -> Dict[str, Any] | None:
        
        # Access safely as a dict (runtime guarantees usage of FrustrationState schema)
        consecutive = state.get("consecutive_flags", 0)
        
        if consecutive >= 3:
            print(f"--- [GUARD] Frustration Limit ({consecutive}). Injecting Override. ---")
            override_msg = SystemMessage(
                content="SYSTEM OVERRIDE: User is stuck. DO NOT ask again. CALL `skip_current_question`."
            )
            return {
                "messages": [override_msg] 
            }
        return None

import time
@dynamic_prompt
def survey_persona_prompt(request: ModelRequest) -> str:
    """
    Dynamically builds the system prompt based on the current AgentState.
    Injects persona, unasked questions, and current question details.
    """
    start_time = time.time()
    state = request.state

    # --- Start with Base Persona ---
    # It provides the core instructions for the agent's behavior.
    prompt_parts = [BASE_PERSONA]

    # --- Inject Persona from State ---
    # This gives the agent its specific character for the conversation.
    persona = state.get("persona")
    if persona:
        prompt_parts.append(f'\n--- CURRENT PERSONA ---\nYour assigned persona is: "{persona}"')

    # --- Inject Dynamic Survey Context ---
    prompt_parts.append("\n--- SURVEY CONTEXT ---")
    
    responses = state.get("responses", {})
    all_questions = state.get("questions", [])

    # 1. Unasked Questions with Choices
    unasked_keys = [r['questionKey'] for r in responses.values() if r.get('status') == 'UNASKED']
    if unasked_keys:
        prompt_parts.append("Remaining question keys:")
        for key in unasked_keys:
            q_obj = next((q for q in all_questions if q.get("questionKey") == key), None)
            if q_obj:
                detail = f"  - {key}"
                q_options = q_obj.get('options')
                if q_options and q_obj.get('questionType') == 'mcq':
                    formatted_choices = []
                    for choice in q_options:
                        if isinstance(choice, dict) and "label" in choice and "value" in choice:
                            formatted_choices.append(f"{choice['label']} ({choice['value']})")
                        else:
                            formatted_choices.append(str(choice))
                    detail += f" [Choices: {', '.join(formatted_choices)}]"
                prompt_parts.append(detail)
    else:
        prompt_parts.append("All questions have been addressed.")

    # 2. Current Question Details
    current_key = state.get("current_question_key")
    if current_key:
        # all_questions has been fetched above
        q_obj = next((q for q in all_questions if q.get("questionKey") == current_key), None)
        
        if q_obj:
            q_text = q_obj.get('questionText', 'N/A')
            # q_options = q_obj.get('options')
            q_validation = q_obj.get('validationRule', 'N/A')
            
            prompt_parts.append(f"Current Focus: '{current_key}'")
            prompt_parts.append(f'  - Question: "{q_text}"')
            # Uncomment to show options in context if needed
            # if q_options:
            #     if q_obj.get("questionType") == "mcq":
            #         # Format MCQ choices for readability
            #         formatted_choices = []
            #         for choice in q_options:
            #             if isinstance(choice, dict) and "label" in choice and "value" in choice:
            #                 formatted_choices.append(f"{choice['label']} ({choice['value']})")
            #             else:
            #                 formatted_choices.append(str(choice))
            #         prompt_parts.append(f"  - Choices: {', '.join(formatted_choices)}")
            #     else:
            #         # For other question types, or if mcq options are not dicts with label/value
            #         prompt_parts.append(f"  - Choices: {q_options}")
            if q_validation:
                prompt_parts.append(f"  - Validation: {q_validation}")
    else:
        prompt_parts.append("Current Focus: None. Get the next question.")

    # --- Final Prompt ---
    # This will be injected as a SystemMessage.
    final_prompt = "\n".join(prompt_parts)
    # print(f"\n[DYNAMIC PROMPT] Generated Prompt:\n{final_prompt}\n") # DEBUG
    print(f"DEBUG: survey_persona_prompt generation took {time.time() - start_time:.4f}s")
    return final_prompt

# Define the cleanup middleware at the module level
cleanup_middleware = ContextEditingMiddleware(
    edits=[
        ClearToolUsesEdit(
            trigger=2000,      # Trigger cleanup when token size exceeds 2000s
            keep=4,          # Always keep the last 4 tool calls (max parallel tool calls)
            # exclude_tools=["save_answer"], # keep save_answer outputs they are critical memory
            placeholder="[Archive Tool Log]" # Replace old tool outputs with this text
        )
    ]
)


# =======================================================
# 3. BUILD AGENT
# =======================================================

# def build_survey_graph(db_client: firestore.AsyncClient):
def build_survey_graph(redis_client=None):
    t_start = time.time()
    model = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        # thinking_level="low",
    )
    # Initialize Async Checkpointer using the shared async client
    # checkpointer = AsyncFirestoreSaver(client=db)
    
    # If no client provided, creating a new one (important for Flask request isolation)
    if redis_client is None:
        redis_client = get_redis_client()

    # checkpointer = AsyncRedisSaver(redis_client=redis_client)
    checkpointer = InMemorySaver()
    app = create_agent(
        model=model, # change model as required
        tools=TOOLS,
        state_schema=CoreSurveyState,
        checkpointer=checkpointer,  # Enable persistent async checkpointer
        
        middleware=[
            bootstrap_session_middleware,
            survey_persona_prompt, 
            # FrustrationGuardMiddleware(),
            # cleanup_middleware # Future use to prune tool messages from history
        ],
    )
    print(f"DEBUG: build_survey_graph inner took {time.time() - t_start:.4f}s")
    
    return app


    # chat = ChatXAI(
    #     model="grok-4-1-fast-reasoning",
    #     temperature=0,
    #     max_tokens=None,
    #     timeout=None,
    #     max_retries=2,
    # )
    