# tools.py
import json
import os
from typing import Any, List, Dict, Optional, Literal, cast, Union

# Updated Imports for ToolRuntime
from langchain.tools import tool, ToolRuntime
from langgraph.types import Command
from langchain.messages import ToolMessage, AnyMessage

# Local Imports 
from my_agent.state import QuestionObj, ResponseObj
from core.database import (
    init_session,
    update_response_in_db,
    update_session_lifecycle,
    get_form_schema
)

# --- Helper: Load JSON Schema from directory---
# Change to load from firestore
async def _load_json_schema(form_id: str) -> Dict[str, Any]:
    """Helper to read the raw JSON file."""
    schema = await get_form_schema(form_id)
    if not schema:
        raise ValueError(f"Form with ID '{form_id}' not found in the database.")
    return schema

# --- SAFE STATE ACCESS HELPER ---
def get_session_info(runtime: ToolRuntime) -> tuple[str, str]:
    """
    Safely retrieves session_id and form_id.
    1. Checks runtime.state (Primary)
    2. Fallback to runtime.config (Reliable for thread_id and initial form_id)
    """
    # Try fetching from state
    session_id = runtime.state.get("session_id")
    form_id = runtime.state.get("form_id")

    # Fallback: LangGraph always has the thread_id in config if persistence is on
    if not session_id:
        session_id = runtime.config.get("configurable", {}).get("thread_id", "Thread ID not found")
        # print("SessionID runtime config")

    # Fallback for form_id: Check config if not in state
    if not form_id:
        form_id = runtime.config.get("configurable", {}).get("form_id","Form ID not found")
        # print("FormID runtime config")

    return session_id, cast(str, form_id)

# =======================================================
# TOOL 1: LOAD SURVEY (Bootstrap)
# =======================================================

@tool
async def load_survey(
    runtime: ToolRuntime
):
    """
    Bootstraps the session. Loads the form schema and any existing answers.
    Call this FIRST if the survey is not loaded.
    """
    # Use Safe Helper
    existing_questions = runtime.state.get("questions", [])
    if len(existing_questions) > 0:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="SYSTEM NOTICE: Survey is ALREADY loaded. Do NOT call load_survey. Proceed to get_next_question.",
                        tool_call_id=runtime.tool_call_id,
                        tool_name="load_survey"
                    )
                ]
            }
        )
    session_id, form_id = get_session_info(runtime)
    
    print(f"--- [TOOL] Loading Survey for {session_id} ---")
    
    try:
        raw_schema = await _load_json_schema(form_id)
    except ValueError as e:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"SYSTEM ERROR: {str(e)} Cannot proceed.",
                        tool_call_id=runtime.tool_call_id,
                        tool_name="load_survey"
                    )
                ]
            }
        )

    persona = raw_schema.get("persona", "You are a friendly survey agent.")
    
    # Create a list of question objects
    questions_list: List[QuestionObj] = [
        {
            "questionKey": q["questionKey"],
            "questionText": q["questionText"],
            "questionType": q["questionType"],
            "options": q["responseOptions"].get("choices", q["responseOptions"]),
            "validationRule": q["responseDataValidationRule"],
        }
        for q in raw_schema.get("questions", [])
    ]

    # Load session from DB and merge into an initial response dictionary
    session_doc = await init_session(session_id, form_id)
    db_responses = session_doc.get("responses", {})

    initial_responses = {
        q["questionKey"]:
            {
                "questionKey": q["questionKey"],
                "value": db_responses.get(q["questionKey"], {}).get("value"),
                "status": db_responses.get(q["questionKey"], {}).get("status", "UNASKED"),
            }
        for q in questions_list
    }
    
    # Determine if it's a new session to set the first question
    is_new_session = not bool(db_responses)
    first_unasked_question_key = next((key for key, resp in initial_responses.items() if resp["status"] == "UNASKED"), None)

    # Acknowledge tool execution
    ack = ToolMessage(
        content=f"Survey loaded successfully. {len(questions_list)} questions available.",
        tool_call_id=runtime.tool_call_id,
        tool_name="load_survey"
    )

    update_dict = {
        "session_id": session_id,
        "form_id": form_id,
        "questions": questions_list,
        "session_state": "ONGOING",
        "responses": initial_responses,
        "persona": persona,
        "consecutive_flags": 0,
        "messages": [ack],
    }
    
    if is_new_session and first_unasked_question_key:
        update_dict["current_question_key"] = first_unasked_question_key
        update_dict["current_question_status"] = "ASKED"
        # Also update the status of the first question in the responses dict
        initial_responses[first_unasked_question_key]["status"] = "ASKED"

    return Command(update=update_dict)


# =======================================================
# HELPER: FIND NEXT QUESTION
# =======================================================
def _find_next_question(
    questions: List[QuestionObj], 
    responses: Dict[str, ResponseObj]
) -> tuple[Optional[str], Optional[str], str]:
    """
    Determines the next question to ask based on current response statuses.
    
    Returns:
        A tuple containing:
        - The key of the next question (or None if finished).
        - The new status for that question ('ASKED' or None).
        - A descriptive message.
    """
    # Pass 1: Find the first "UNASKED" question in order.
    next_q_key = next((q["questionKey"] for q in questions if responses.get(q["questionKey"], {}).get("status") == "UNASKED"), None)
    if next_q_key:
        q_details = next(q for q in questions if q["questionKey"] == next_q_key)
        return next_q_key, "ASKED", f"Next Question: {q_details['questionText']}"

    # Pass 2: If no "UNASKED", find an "ASKED" one to retry.
    reask_q_key = next((q["questionKey"] for q in questions if responses.get(q["questionKey"], {}).get("status") == "ASKED"), None)
    if reask_q_key:
        q_details = next(q for q in questions if q["questionKey"] == reask_q_key)
        return reask_q_key, "ASKED", f"Re-asking: {q_details['questionText']}"

    # Pass 3: If no questions are UNASKED or ASKED, the survey is finished.
    return None, None, "No unasked questions remaining. The survey is complete."


# =======================================================
# TOOL 2: SAVE ANSWER (The Pen & The Compass)
# =======================================================

@tool
async def save_answer(
    answers: List[Dict[str, Any]],
    runtime: ToolRuntime,
) -> Command:
    """
    Validates and saves a list of answers. `answers` must be a list of dicts,
    each with "question_key" and "value" keys.
    Example: [{"question_key": "displayName", "value": "test"}, {"question_key": "yearsOfExperience", "value": 8}]
    
    If a valid answer for the current question is provided, it automatically finds the next question.
    Processes all answers, saves valid ones, and reports any errors.
    """
    session_id, _ = get_session_info(runtime)
    questions = runtime.state.get("questions", [])
    responses = runtime.state.get("responses", {})
    current_question_key = runtime.state.get("current_question_key")

    response_update: Dict[str, Any] = {}
    ack_messages: List[str] = []
    error_messages: List[str] = []
    
    current_question_answered_validly = False

    for answer in answers:
        question_key = cast(str, answer.get("question_key"))
        value = answer.get("value")

        if not question_key or value is None:
            error_messages.append(f"Invalid answer format in list: {answer}")
            continue
        
        target_q = next((q for q in questions if q["questionKey"] == question_key), None)
        if not target_q:
            error_messages.append(f"Error: Question key '{question_key}' does not exist.")
            continue

        # --- Validation Logic ---
        validation_error = None
        if target_q["questionType"] == "mcq":
            # Get original valid values and a lowercased version for matching
            original_valid_values = [opt["value"] if isinstance(opt, dict) else opt for opt in (target_q.get("options") or [])]
            lower_valid_values = [str(v).lower() for v in original_valid_values]
            
            # Normalize user input to a list, but remember if it was originally a list
            was_list = isinstance(value, list)
            values_to_check = value if was_list else [value]
            
            final_value_list = []
            
            # Process each item from the user's answer
            for item in values_to_check:
                try:
                    # If it matches a valid option case-insensitively, use the canonical option value
                    idx = lower_valid_values.index(str(item).lower())
                    final_value_list.append(original_valid_values[idx])
                except ValueError:
                    # If it's not a valid option, append the user's answer as-is
                    final_value_list.append(item)
            
            # Finalize the value, respecting original format (list or single item)
            if was_list:
                value = final_value_list
            else:
                value = final_value_list[0] if final_value_list else None
        
        elif target_q["questionType"] in ["integer", "rating"]:
            if isinstance(value, list):
                validation_error = f"Error for '{question_key}': Expected a single number, got a list: {value}."
            else:
                try:
                    int_val = int(value)
                    opts = target_q.get("options")
                    if isinstance(opts, dict):
                        min_val, max_val = opts.get("min"), opts.get("max")
                        if min_val is not None and int_val < min_val: validation_error = f"Error for '{question_key}': Must be >= {min_val}."
                        if max_val is not None and int_val > max_val: validation_error = f"Error for '{question_key}': Must be <= {max_val}."
                    elif isinstance(opts, list) and len(opts) > 0:
                        valid_values = [opt["value"] if isinstance(opt, dict) else opt for opt in opts]
                        if int_val not in valid_values:
                            min_v, max_v = min(valid_values), max(valid_values)
                            validation_error = f"Error for '{question_key}': Rating must be between {min_v} and {max_v}."
                except (ValueError, TypeError):
                    validation_error = f"Error for '{question_key}': '{value}' is not a valid integer."
        
        if validation_error:
            # Construct detailed error message
            detailed_error_msg = f"{validation_error}\n"
            detailed_error_msg += f"Question: '{target_q['questionText']}'\n"
            if target_q.get('options'):
                if target_q["questionType"] == "mcq":
                    formatted_choices = []
                    for choice in target_q['options']:
                        if isinstance(choice, dict) and "label" in choice and "value" in choice:
                            formatted_choices.append(f"{choice['label']} ({choice['value']})")
                        else:
                            formatted_choices.append(str(choice))
                    detailed_error_msg += f"Available Choices: {', '.join(formatted_choices)}\n"
                elif target_q["questionType"] in ["integer", "rating"] and isinstance(target_q['options'], dict):
                    min_val = target_q['options'].get("min")
                    max_val = target_q['options'].get("max")
                    if min_val is not None and max_val is not None:
                        detailed_error_msg += f"Expected Range: {min_val} to {max_val}\n"
                    elif min_val is not None:
                        detailed_error_msg += f"Minimum Value: {min_val}\n"
                    elif max_val is not None:
                        detailed_error_msg += f"Maximum Value: {max_val}\n"
                else: # Fallback for other types or unexpected formats
                    detailed_error_msg += f"Options: {target_q['options']}\n"

            if target_q.get('validationRule'):
                detailed_error_msg += f"Validation Rule: {target_q['validationRule']}"
            
            error_messages.append(detailed_error_msg)
            continue
            
        # --- Persist Answer & Prep State ---
        await update_response_in_db(session_id, question_key, value, "ANSWERED")
        response_update[question_key] = {
            **(responses.get(question_key, {})),
            "questionKey": question_key,
            "value": value,
            "status": "ANSWERED",
        }
        ack_messages.append(f"Saved answer for '{question_key}'.")
        
        if question_key == current_question_key:
            current_question_answered_validly = True
            
    # --- Combine messages for the tool output ---
    final_message_parts = ack_messages + error_messages

    # --- Decide on next step ---
    # Only find the next question if the user answered the *current* one.
    if not current_question_answered_validly:
        final_message = "\n".join(final_message_parts) if final_message_parts else "No valid answers provided to save."
        ack = ToolMessage(content=final_message, tool_call_id=runtime.tool_call_id, tool_name="save_answer")
        return Command(update={"responses": response_update, "messages": [ack]})

    # --- Find Next Question using Helper ---
    temp_responses = {**responses, **response_update}
    next_q_key, new_status, message = _find_next_question(questions, temp_responses)
    
    final_message_parts.append(message)
    ack = ToolMessage(content="\n".join(final_message_parts), tool_call_id=runtime.tool_call_id, tool_name="save_answer")

    # If a next question is found, update its state.
    if next_q_key and new_status:
        response_update[next_q_key] = {
            **(temp_responses.get(next_q_key, {})),
            "questionKey": next_q_key,
            "status": new_status,
        }
        return Command(
            update={
                "responses": response_update,
                "current_question_key": next_q_key,
                "current_question_status": new_status,
                "messages": [ack],
            }
        )
    else: # Survey is finished
        return Command(
            update={
                "responses": response_update,
                "session_state": "FINISHED",
                "current_question_key": None,
                "current_question_status": "None",
                "messages": [ack],
            }
        )



# =======================================================
# TOOL 3.2: skip current question
# =======================================================

@tool
async def skip_current_question(runtime: ToolRuntime) -> Command:
    """
    Marks the current question as SKIPPED.
    Does NOT move the pointer.
    """
    session_id, _ = get_session_info(runtime)
    current_key = runtime.state.get("current_question_key")

    if not current_key:
        return Command(update={"messages": [ToolMessage(content="No active question to skip.", tool_call_id=runtime.tool_call_id, tool_name="skip_current_question")]})

    await update_response_in_db(session_id, current_key, None, "SKIPPED")

    # Construct the partial update
    response_update = {
        current_key: {
            "questionKey": current_key,
            "value": None,
            "status": "SKIPPED"
        }
    }
    
    ack = ToolMessage(content=f"Question '{current_key}' skipped.", tool_call_id=runtime.tool_call_id, tool_name="skip_current_question")

    return Command(
        update={
            "responses": response_update,
            "messages": [ack],
        }
    )
    
# =======================================================
# TOOL 4: UPDATE QUESTION STATE (The Pointer)
# =======================================================

@tool
async def update_question_state(
    target_question_key: str,
    new_status: Literal["CLARIFYING", "SKIPPED"],
    runtime: ToolRuntime,
) -> Command:
    """
    Updates the question state to CLARIFYING or SKIPPED.
    - CLARIFYING: Marks the question for clarification without changing its value or saving answer
    - SKIPPED: Marks the question as skipped and moves to the next one.
    """
    session_id, _ = get_session_info(runtime)

    if new_status == "CLARIFYING":
        updates: Dict[str, Any] = {
            "current_question_key": target_question_key,
            "current_question_status": new_status,
        }
        updates["consecutive_flags"] = runtime.state.get("consecutive_flags", 0) + 1
        msg = f"Clarifying response for question '{target_question_key}'."
        
        ack = ToolMessage(
            content=msg,
            tool_call_id=runtime.tool_call_id,
            tool_name="update_question_state",
        )

        return Command(
            update={
                **updates,
                "messages": cast(List[AnyMessage], [ack]),
            }
        )
    
    elif new_status == "SKIPPED":
        questions = runtime.state.get("questions", [])
        responses = runtime.state.get("responses", {})

        # Mark the target question as SKIPPED
        await update_response_in_db(session_id, target_question_key, None, "SKIPPED")
        response_update = {
            target_question_key: {
                **(responses.get(target_question_key, {})),
                "questionKey": target_question_key,
                "value": None,
                "status": "SKIPPED",
            }
        }
        
        # --- Find Next Question using Helper ---
        temp_responses = {**responses, **response_update}
        next_q_key, next_q_status, message = _find_next_question(questions, temp_responses)
        
        ack_message = f"Question '{target_question_key}' skipped. {message}"
        ack = ToolMessage(content=ack_message, tool_call_id=runtime.tool_call_id, tool_name="update_question_state")

        final_update = {"responses": response_update, "messages": [ack]}

        # If a next question is found, update its state.
        if next_q_key and next_q_status:
            response_update[next_q_key] = {
                **(temp_responses.get(next_q_key, {})),
                "questionKey": next_q_key,
                "status": next_q_status,
            }
            final_update["current_question_key"] = next_q_key
            final_update["current_question_status"] = next_q_status
        else: # Survey is finished
            final_update["session_state"] = "FINISHED"
            final_update["current_question_key"] = None
            final_update["current_question_status"] = "None"
        
        return Command(update=final_update)

    # This path should ideally not be taken if new_status is correctly validated.
    return Command(update={})


# =======================================================
# LIFECYCLE TOOLS
# =======================================================

@tool
async def end_survey(reason: str, runtime: ToolRuntime) -> Command:
    """Ends the survey session."""
    session_id, _ = get_session_info(runtime)
    await update_session_lifecycle(session_id, "FINISHED")
    ack = ToolMessage(content=f"Survey ended. Reason: {reason}", tool_call_id=runtime.tool_call_id, tool_name="end_survey")
    return Command(update={"session_state": "FINISHED", "messages": [ack]})

@tool
async def update_session_state(
    status: Literal["ONGOING"],
    runtime: ToolRuntime
) -> Command:
    """Update session state to ONGOING when a new session starts"""
    session_id, _ = get_session_info(runtime)
    try:
        await update_session_lifecycle(session_id, status)
    except ValueError:
        pass
    ack = ToolMessage(content=f"Session state updated to {status}.", tool_call_id=runtime.tool_call_id, tool_name="update_session_state")
    return Command(update={"session_state": status, "messages": [ack]})
    
@tool
def get_all_questions(runtime: ToolRuntime) -> str:
    """
    Retrieves a full summary of the survey questions and their current status.
    Use this when the user asks about progress, remaining questions, or wants a summary.
    """
    questions = runtime.state.get("questions", [])
    responses = runtime.state.get("responses", {})

    if not questions:
        return "System Notice: No questions are currently loaded. The survey might not have started."

    report = [f"--- SURVEY STATUS SUMMARY (Total: {len(questions)}) ---"]
    
    for idx, q in enumerate(questions, 1):
        key = q["questionKey"]
        
        # Look up response directly by key
        target_resp = responses.get(key)
        
        status = target_resp["status"] if target_resp else "UNASKED"
        value_str = str(target_resp["value"]) if target_resp and target_resp.get("value") is not None else "N/A"

        line = f"{idx}. [{status}] {q['questionText']}"
        if status == "ANSWERED":
            line += f" -> You said: '{value_str}'"
        
        report.append(line)

    return "\n".join(report)