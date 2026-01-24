import os
import sys
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

# Setup paths and logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import your existing agent logic
try:
    from my_agent.graph import build_survey_graph
except ImportError as e:
    logger.error(f"Import failed: {e}")
    build_survey_graph = None

app = FastAPI()

# --- Data Models ---
class ChatRequest(BaseModel):
    session_id: str
    message: str
    form_id: Optional[str] = None

class StateRequest(BaseModel):
    session_id: str

# --- Helper to Extract Chips ---
def extract_chips(state: Dict[str, Any]) -> Dict[str, Any]:
    current_key = state.get("current_question_key")
    questions = state.get("questions", [])
    if not current_key or not questions:
        return {"show_chips": False, "options": []}
    
    q_def = next((q for q in questions if q.get("questionKey") == current_key), None)
    if not q_def: return {"show_chips": False, "options": []}

    q_type = q_def.get("questionType")
    options = q_def.get("responseOptions", {}).get("choices", []) if q_def.get("responseOptions") else q_def.get("options", [])
    
    # Logic to format options for Frontend
    if q_type in ["mcq", "rating"] and isinstance(options, list):
        formatted = []
        for opt in options:
            if isinstance(opt, dict): 
                formatted.append({"label": opt.get("label", str(opt.get("value"))), "value": opt.get("value")})
            else: 
                formatted.append({"label": str(opt), "value": opt})
        return {"show_chips": True, "chip_type": q_type, "options": formatted}
    
    if q_type == "boolean":
        return {"show_chips": True, "chip_type": "yes_no", "options": [{"label": "Yes", "value": True}, {"label": "No", "value": False}]}
        
    return {"show_chips": False, "options": []}

# --- Routes ---
@app.get("/")
def health(): return {"status": "ok", "service": "barmuda-agent"}

@app.post("/chat")
async def chat(req: ChatRequest):
    if not build_survey_graph:
        raise HTTPException(status_code=500, detail="Agent logic not loaded")

    try:
        # No Redis client passed - assumes graph.py handles this (e.g. uses MemorySaver)
        graph = build_survey_graph() 
        config = {"configurable": {"thread_id": req.session_id, "form_id": req.form_id}}
        
        # Run Agent
        input_data = {"messages": [HumanMessage(content=req.message)]}
        final_state = await graph.ainvoke(input_data, config=config)
        
        # Extract Text Response
        agent_response = "I'm sorry, I couldn't process that."
        if final_state.get("messages"):
            # Find the last AIMessage that has content
            for msg in reversed(final_state["messages"]):
                if isinstance(msg, AIMessage) and msg.content:
                    agent_response = str(msg.content)
                    break

        return {
            "success": True,
            "response": agent_response,
            "chip_options": extract_chips(final_state),
            "session_id": req.session_id,
            "ended": final_state.get("session_state") == "FINISHED",
            "metadata": {
                "current_question": final_state.get("current_question_key"),
                "status": final_state.get("current_question_status")
            }
        }
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return {"success": False, "error": str(e), "response": "Error processing request."}

@app.post("/state")
async def get_state(req: StateRequest):
    if not build_survey_graph:
        raise HTTPException(status_code=500, detail="Agent logic not loaded")

    try:
        graph = build_survey_graph()
        config = {"configurable": {"thread_id": req.session_id}}
        state_snapshot = await graph.aget_state(config)
        
        if not state_snapshot.values: 
            return {"success": False, "error": "No state found"}
        
        final_state = state_snapshot.values
        
        # Format history (simplified)
        history = []
        for msg in final_state.get("messages", []):
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage) and msg.content:
                history.append({"role": "assistant", "content": str(msg.content)})

        return {
            "success": True,
            "session_id": req.session_id,
            "chip_options": extract_chips(final_state),
            "history": history,
            "metadata": {
                "current_question": final_state.get("current_question_key"),
                "status": final_state.get("current_question_status"),
                "session_state": final_state.get("session_state")
            }
        }
    except Exception as e:
        logger.error(f"State error: {e}")
        return {"success": False, "error": str(e)}