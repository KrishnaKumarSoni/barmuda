"""
Streaming wrapper for chat agent responses
Adds streaming capability without modifying the existing agent architecture
"""

import time
import json
import re
from typing import Generator, Dict, Any


def simulate_typing_stream(text: str, chunk_size: int = 2) -> Generator[str, None, None]:
    """
    Stream text in word groups for natural typing effect
    
    Args:
        text: The complete text to stream
        chunk_size: Number of words per chunk (default 2 for better streaming effect)
    
    Yields:
        String chunks of the text (word groups)
    """
    if not text:
        return
    
    words = text.split()
    
    # Stream in smaller word groups for more natural streaming effect
    for i in range(0, len(words), chunk_size):
        chunk_words = words[i:i + chunk_size]
        chunk_text = ' '.join(chunk_words)
        yield chunk_text
        
        # Add space between chunks (except for last chunk)
        if i + chunk_size < len(words):
            yield " "


def stream_agent_response(agent, session_id: str, message: str) -> Generator[Dict[str, Any], None, None]:
    """
    Stream the response from an existing agent without modifying its architecture
    
    This function:
    1. Runs the existing agent normally (all tools execute)
    2. Takes the complete response
    3. Streams it character by character for better UX
    4. Preserves all existing functionality
    
    Args:
        agent: The existing FormChatAgent instance
        session_id: Chat session ID
        message: User message
    
    Yields:
        Dictionary chunks with streaming data
    """
    try:
        # First, yield a "processing" indicator
        yield {
            "type": "processing",
            "message": "Agent is thinking..."
        }
        
        # Run the existing agent normally - ALL TOOLS EXECUTE HERE
        # This preserves the entire agentic architecture
        print(f"🔄 STREAMING: About to call agent.process_message for session {session_id}")
        print(f"🔄 STREAMING: Message: {message}")
        
        result = agent.process_message(session_id, message)
        
        print(f"🔄 STREAMING: Agent returned result: {result.get('success', False)}")
        print(f"🔄 STREAMING: Response text length: {len(result.get('response', ''))}")
        
        # Check if agent processing was successful
        if not result.get("success"):
            yield {
                "type": "error",
                "message": result.get("error", "Agent processing failed")
            }
            return
        
        # Signal that we're starting to stream the response
        yield {
            "type": "start_response",
            "message": "Streaming response..."
        }
        
        # Get the complete response text
        response_text = result.get("response", "")
        
        if not response_text:
            yield {
                "type": "error", 
                "message": "No response text received from agent"
            }
            return
        
        # Stream the response text naturally
        accumulated_text = ""
        for chunk in simulate_typing_stream(response_text):
            accumulated_text += chunk
            yield {
                "type": "text_chunk",
                "chunk": chunk,
                "accumulated": accumulated_text
            }
        
        # Signal completion and include full result for frontend processing
        yield {
            "type": "complete",
            "message": "Response complete",
            "full_result": result,  # Include full agent result for frontend
            "final_text": response_text
        }
        
    except Exception as e:
        yield {
            "type": "error",
            "message": f"Streaming error: {str(e)}"
        }


def format_sse_data(data: Dict[str, Any]) -> str:
    """
    Format data for Server-Sent Events
    
    Args:
        data: Dictionary to send via SSE
    
    Returns:
        Formatted SSE string
    """
    return f"data: {json.dumps(data)}\n\n"


class StreamingChatManager:
    """
    Manages streaming chat responses while preserving existing agent architecture
    """
    
    def __init__(self, agent):
        """
        Initialize with existing agent
        
        Args:
            agent: The existing FormChatAgent instance
        """
        self.agent = agent
    
    def stream_message(self, session_id: str, message: str) -> Generator[str, None, None]:
        """
        Stream a chat message response using SSE format
        
        Args:
            session_id: Chat session ID
            message: User message
        
        Yields:
            SSE-formatted data strings
        """
        for chunk_data in stream_agent_response(self.agent, session_id, message):
            yield format_sse_data(chunk_data)
    
    def process_message_fallback(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Fallback to non-streaming mode (calls existing agent directly)
        
        Args:
            session_id: Chat session ID  
            message: User message
            
        Returns:
            Standard agent response
        """
        return self.agent.process_message(session_id, message)