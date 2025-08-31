"""
Simple Chat Agent for Natural Conversation Flow
Fixes the issue where responses don't feel natural to user messages
"""

import json
import os
from datetime import datetime
from typing import Any, Dict

import openai
from chat_agent_v2 import load_session, save_session, ChatSession

def get_openai_client():
    """Get OpenAI client"""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found")
    return openai.OpenAI(api_key=api_key)

def process_message_naturally(session_id: str, user_message: str) -> Dict[str, Any]:
    """Process user message with natural conversation flow"""
    try:
        # Load session
        session = load_session(session_id)
        client = get_openai_client()
        
        # Add user message to history
        session.chat_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Get current question
        current_q_idx = session.current_question_index
        questions = session.form_data.get("questions", [])
        current_question = ""
        
        if current_q_idx < len(questions):
            current_question = questions[current_q_idx]["text"]
        
        # Build conversation context
        recent_history = session.chat_history[-10:]  # Last 10 messages
        conversation_context = ""
        for msg in recent_history[:-1]:  # Exclude the just-added user message
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation_context += f"{role}: {msg['content']}\n"
        
        # Handle confirmation state first
        if session.metadata.get("state") == "confirmation_pending":
            user_lower = user_message.lower().strip()
            if any(word in user_lower for word in ["yes", "yeah", "sure", "ok", "okay"]):
                intent = "confirm_end"
                action = "end_survey"
                natural_response = f"Got it! Thanks for your time and feedback."
            else:
                intent = "continue" 
                action = "continue_survey"
                natural_response = f"No problem! Let's continue where we left off."
        else:
            # GPT-POWERED INTENT DETECTION (from your original agent)
            try:
                intent, action, natural_response = detect_intent_with_gpt(user_message, current_question)
            except Exception as gpt_error:
                print(f"GPT intent detection failed: {str(gpt_error)}, using fallback")
                # Fallback to simple detection
                user_lower = user_message.lower().strip()
                
                # Determine intent and action
                if any(word in user_lower for word in ["skip", "pass", "next", "don't want", "won't answer"]):
                    intent = "skip"
                    action = "skip_question"
                    natural_response = generate_skip_response_with_gpt(user_message)
                elif any(word in user_lower for word in ["done", "stop", "quit", "end", "finish", "enough"]):
                    intent = "end"
                    action = "end_survey" 
                    natural_response = "I understand you'd like to finish up. Are you sure you want to end the survey? (Just say 'yes' to confirm or 'no' to continue)"
                elif current_question and user_message.strip():
                    intent = "answer"
                    action = "save_response"
                    # GPT-powered natural acknowledgment
                    natural_response = generate_acknowledgment_with_gpt(user_message, current_question)
                else:
                    intent = "clarify"
                    action = "ask_clarification"
                    natural_response = "Could you help me understand your response a bit better?"
            
        analysis = {
            "intent": intent,
            "action": action,
            "natural_response": natural_response
        }
        
        # Execute the determined action
        action_taken = False
        
        if analysis["action"] == "save_response" and current_question:
            # Save the response
            session.responses[str(current_q_idx)] = {
                "value": user_message,
                "timestamp": datetime.now().isoformat(),
                "question_text": current_question,
            }
            session.current_question_index += 1
            action_taken = True
            
        elif analysis["action"] == "skip_question":
            # Skip current question
            session.responses[str(current_q_idx)] = {
                "value": "[SKIP]",
                "timestamp": datetime.now().isoformat(),
                "reason": "user_request",
            }
            session.metadata["skip_count"] = session.metadata.get("skip_count", 0) + 1
            session.current_question_index += 1
            action_taken = True
            
        elif analysis["action"] == "end_survey" and analysis["intent"] != "confirm_end":
            # Set confirmation state (not actual ending)
            session.metadata.update({
                "state": "confirmation_pending",
                "confirmation_type": "end_survey"
            })
            
        elif analysis["action"] == "end_survey" and analysis["intent"] == "confirm_end":
            # Actually end the survey
            session.metadata.update({
                "ended": True,
                "end_time": datetime.now().isoformat(),
                "state": "normal"
            })
            action_taken = True
            
        elif analysis["action"] == "continue_survey":
            # Clear confirmation state and continue
            session.metadata.update({
                "state": "normal",
                "confirmation_type": None
            })
            
        # Generate natural response
        next_question = ""
        if action_taken and session.current_question_index < len(questions) and not session.metadata.get("ended"):
            next_question = questions[session.current_question_index]["text"]
        elif action_taken and session.current_question_index >= len(questions) and not session.metadata.get("ended"):
            # Survey completed naturally
            session.metadata["ended"] = True
            session.metadata["end_time"] = datetime.now().isoformat()
            
        # Build final response
        if session.metadata.get("ended"):
            final_response = f"{analysis['natural_response']} Thank you for completing our survey! 🎉"
        elif session.metadata.get("state") == "confirmation_pending":
            final_response = analysis["natural_response"] 
        elif next_question and action_taken:
            final_response = f"{analysis['natural_response']} Now, {next_question}"
        else:
            final_response = analysis["natural_response"]
        
        # Add response to history
        session.chat_history.append({
            "role": "assistant",
            "content": final_response,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Save session
        save_session(session)
        
        return {
            "success": True,
            "response": final_response,
            "session_updated": True,
            "metadata": session.metadata,
        }
        
    except Exception as e:
        print(f"Natural chat processing error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "error": str(e),
            "response": "I'm having trouble right now. Could you try again? 😅",
        }