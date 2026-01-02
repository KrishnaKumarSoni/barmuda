import asyncio
# from google.cloud import firestore
from my_agent.graph import build_survey_graph
# from database import db as db_client  # Shared Async Firestore Client
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from typing import Dict, Any, List, cast

async def main():
    # 1. Initialize Async Firestore Client ONCE
    # This pool is shared between the Checkpointer and your Tools (via database.py)
    
    # 2. Build graph with the client
    # app = build_survey_graph(db_client)
    app = build_survey_graph()

    # 3. Config with thread_id
    thread_id = "sess-1013"
    FORM_ID = "form_number_1"
    config: RunnableConfig = {
        "configurable": {
            "thread_id": thread_id,
            "form_id": FORM_ID, 
        }
    }

    print("--- Starting Session ---")
    
    print(f"--- Starting Session (Thread ID: {thread_id}) ---")
    print("Type 'exit', 'quit', or 'q' to end the session.\n")
     # 3. Fetch and Print Existing History
    # app.aget_state(config) fetches the state from Redis without running the agent
    state_snapshot = await app.aget_state(config)
    
    if state_snapshot.values:
        print("\n--- Resuming Previous Session ---")
        messages = state_snapshot.values.get("messages", [])
        
        # Iterate through history and print nicely
        for msg in messages:
            if isinstance(msg, HumanMessage):
                # print(f"You: {msg.content}")
                print(f"You: {msg.content}")
            elif isinstance(msg, AIMessage):
                # Only print content, ignore tool calls for clarity in this view
                if msg.content:
                    print(f"Agent: {msg.content}")
            elif isinstance(msg, ToolMessage):
                print(f"   [Tool Output]: {msg.content[:50]}...") # Truncate for readability
        print("---------------------------------\n")
    else:
        print("--- New Session Started ---\n")

    print("Type 'exit', 'quit', or 'q' to end the session.\n")
    # 4. CLI Loop
    while True:
        # try:
            # Use run_in_executor to avoid blocking the async event loop with input()
            user_input = await asyncio.get_running_loop().run_in_executor(None, input, "You: ")
            user_input = user_input.strip()

            if user_input.lower() in {"exit", "quit", "q"}:
                print("Ending session. Goodbye!")
                break
            
            if not user_input:
                continue

            # 5. Prepare Input & Fix Pylance Error
            # We explicitly type the list as List[BaseMessage] so Pylance accepts it
            # into the schema which expects List[AnyMessage]
            input_data= {
                "messages": [HumanMessage(content=user_input)]
            }

            # 6. Run the Agent
            # We use 'await' because we are using the AsyncFirestoreSaver
            # stream_mode="values" returns the full state at each step, 
            # allowing us to see the final response easily.
            final_state = await app.ainvoke(cast(Any,input_data), config=config)
            
            # 7. Extract and Print Response
            # The agent's response is typically the last message in the history
            response_message = final_state["messages"][-1]
            print(f"Agent: {response_message.content}\n")

        # except Exception as e:
        #     print(f"An error occurred: {e}")
            # Optional: Decide whether to break or continue based on error severity

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSession interrupted by user.")
        
        
        