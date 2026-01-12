import os
import sys
import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# Add the agent directory to sys.path to allow imports from my_agent
AGENT_ROOT = os.path.join(os.getcwd(), "agent")
if AGENT_ROOT not in sys.path:
    sys.path.append(AGENT_ROOT)

try:
    from my_agent.graph import build_survey_graph
    from core.redis_client import get_redis_client
except ImportError as e:
    logging.error(f"Failed to import LangGraph components: {e}")
    raise

logger = logging.getLogger(__name__)

class ChatAdapter:
    """
    Bridge between Synchronous Flask and Asynchronous LangGraph.
    Handles graph initialization, message processing, and state formatting.
    """

    @classmethod
    async def process_message_async(cls, session_id: str, form_id: str, message: str) -> Dict[str, Any]:
        """
        Asynchronously invokes the graph and processes the resulting state.
        """
        redis_client = get_redis_client()
        try:
            # Resolve form_id if missing (Legacy support)
            if not form_id:
                form_id = await cls._get_form_id_from_db(session_id)
                if not form_id:
                     return {
                        "success": False,
                        "error": "Session not found or form_id missing.",
                        "response": "I'm sorry, I seem to have lost our connection. Please refresh the page."
                    }

            graph = build_survey_graph(redis_client=redis_client)
            
            # Config matching agent/main.py structure
            config = {
                "configurable": {
                    "thread_id": session_id,
                    "form_id": form_id, 
                }
            }

            # Prepare input
            input_data = {
                "messages": [HumanMessage(content=message)]
            }

            # Invoke LangGraph
            # We use ainvoke to get the final state
            final_state = await graph.ainvoke(input_data, config=config)
            
            # 1. Extract the agent's text response
            # The last message in history is usually the AI's response
            messages = final_state.get("messages", [])
            agent_response = "I'm sorry, I couldn't process that."
            
            if messages:
                # Find the last AIMessage that isn't just a tool call
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage) and msg.content:
                        content = msg.content
                        
                        # Handle complex content types (list of blocks)
                        if isinstance(content, list):
                            text_parts = []
                            for block in content:
                                if isinstance(block, dict):
                                    if block.get("type") == "text":
                                        text_parts.append(block.get("text", ""))
                                    elif "text" in block: # Fallback
                                        text_parts.append(block["text"])
                                elif isinstance(block, str):
                                    text_parts.append(block)
                            agent_response = " ".join(text_parts).strip()
                        elif isinstance(content, str):
                            agent_response = content
                        
                        break

            # 2. Extract Chips (Choices) for the frontend
            chip_options = cls._extract_chips(final_state)

            # 3. Check session lifecycle
            session_state = final_state.get("session_state", "ONGOING")
            
            return {
                "success": True,
                "response": agent_response,
                "chip_options": chip_options,
                "session_id": session_id,
                "ended": session_state == "FINISHED",
                "metadata": {
                    "current_question": final_state.get("current_question_key"),
                    "status": final_state.get("current_question_status")
                }
            }

        except Exception as e:
            logger.error(f"Error in LangGraph processing: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "response": "I'm having a bit of trouble connecting to my brain right now. 😅"
            }
        finally:
            await redis_client.aclose()

    @classmethod
    async def get_current_state(cls, session_id: str) -> Dict[str, Any]:
        """
        Retrieves the current state of the session without invoking the graph.
        Useful for checking chips or status.
        """
        redis_client = get_redis_client()
        try:
            form_id = await cls._get_form_id_from_db(session_id)
            if not form_id:
                return {"success": False, "error": "Session not found"}

            graph = build_survey_graph(redis_client=redis_client)
            config = {"configurable": {"thread_id": session_id, "form_id": form_id}}
            
            state_snapshot = await graph.aget_state(config)
            
            if not state_snapshot.values:
                return {"success": False, "error": "No state found"}
                
            final_state = state_snapshot.values
            chip_options = cls._extract_chips(final_state)
            
            # Extract history
            history = []
            for msg in final_state.get("messages", []):
                if isinstance(msg, HumanMessage):
                    history.append({
                        "role": "user",
                        "content": msg.content,
                        "timestamp": None # LangGraph messages don't always have timestamps in kwargs by default
                    })
                elif isinstance(msg, AIMessage) and msg.content:
                    # Filter out empty AI messages (tool calls)
                    history.append({
                        "role": "assistant",
                        "content": msg.content,
                        "timestamp": None
                    })

            return {
                "success": True,
                "session_id": session_id,
                "chip_options": chip_options,
                "history": history,
                "metadata": {
                    "current_question": final_state.get("current_question_key"),
                    "status": final_state.get("current_question_status"),
                    "session_state": final_state.get("session_state")
                }
            }
        except json.JSONDecodeError as e:
            logger.error(f"State corruption detected for session {session_id}: {e}")
            return {"success": False, "error": f"State corrupted: {e}"}
        except Exception as e:
            logger.error(f"Error getting state: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await redis_client.aclose()

    @staticmethod
    async def _get_form_id_from_db(session_id: str) -> Optional[str]:
        """
        Retrieves the form_id associated with a session_id from Firestore.
        Uses executor to prevent blocking the async event loop.
        """
        from web.extensions import db
        try:
            loop = asyncio.get_running_loop()
            
            def fetch_doc():
                doc = db.collection('sessions').document(session_id).get()
                return doc

            doc = await loop.run_in_executor(None, fetch_doc)
            
            if doc.exists:
                return doc.to_dict().get("form_id")
            return None
        except Exception as e:
            logger.error(f"Error fetching form_id for session {session_id}: {e}")
            return None

    @staticmethod
    def _extract_chips(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes the current state to determine if the user should see clickable chips.
        """
        current_key = state.get("current_question_key")
        questions = state.get("questions", [])
        
        if not current_key or not questions:
            return {"show_chips": False, "options": []}

        # Find current question definition
        question_def = next((q for q in questions if q.get("questionKey") == current_key), None)
        
        if not question_def:
            return {"show_chips": False, "options": []}

        q_type = question_def.get("questionType")
        options = question_def.get("options")

        # Handle MCQ
        if q_type == "mcq" and isinstance(options, list):
            formatted_options = []
            for opt in options:
                if isinstance(opt, dict):
                    formatted_options.append({
                        "label": opt.get("label", str(opt.get("value"))),
                        "value": opt.get("value")
                    })
                else:
                    formatted_options.append({"label": str(opt), "value": opt})
            
            return {
                "show_chips": True,
                "chip_type": "mcq",
                "options": formatted_options
            }

        # Handle Boolean (Yes/No)
        if q_type == "boolean":
            return {
                "show_chips": True,
                "chip_type": "yes_no",
                "options": [
                    {"label": "Yes", "value": True},
                    {"label": "No", "value": False}
                ]
            }

        # Handle Rating
        if q_type == "rating":
            if isinstance(options, list):
                formatted_options = []
                for opt in options:
                    if isinstance(opt, dict):
                        formatted_options.append({
                            "label": opt.get("label", str(opt.get("value"))),
                            "value": opt.get("value")
                        })
                    else:
                        formatted_options.append({"label": str(opt), "value": opt})
                
                return {
                    "show_chips": True,
                    "chip_type": "rating",
                    "options": formatted_options
                }
            elif isinstance(options, dict):
                min_val = options.get("min", 1)
                max_val = options.get("max", 5)
                # Only show chips for small scales (e.g., 1-5 or 1-10)
                if (max_val - min_val) <= 10:
                    return {
                        "show_chips": True,
                        "chip_type": "rating",
                        "options": [{"label": str(i), "value": i} for i in range(min_val, max_val + 1)]
                    }

        return {"show_chips": False, "options": []}

def process_chat_message(session_id: str, form_id: str, message: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for Flask routes.
    """
    # Use a new event loop for each request to avoid issues with Flask's threading
    # In production, using asgiref.sync.async_to_sync is preferred
    return asyncio.run(ChatAdapter.process_message_async(session_id, form_id, message))
