# Codebase Refactoring & Agent Migration Plan

## 1. Executive Summary
**Objective:** Migrate the Barmuda application from a monolithic, "vibecoded" structure to a modular, organized Flask architecture. Simultaneously, replace the legacy `chat_engine.py` with a modern, asynchronous **LangGraph** agent located in the `agent/` directory.

**Core Decision:** We will **retain Flask** as the web framework to preserve existing frontend logic and template rendering, but we will introduce an **Adapter Layer** to bridge the synchronous Flask app with the asynchronous LangGraph agent.

---

## 2. Architecture Overview

### Current State ("The Monolith")
*   **`app.py`**: Handles everything (Routing, DB, Auth, Chat, Billing, HTML serving).
*   **`chat_engine.py`**: Tightly coupled, legacy synchronous chat logic.
*   **Issues**: High coupling, difficult to test, mixed responsibilities, no clear separation of concerns.

### Target State ("The Modular Monolith")
We will implement a layered architecture that separates the **Web Interface** from the **Business Logic** and the **AI Agent**.

```text
/home/onesine/gitClone/barmuda/
│
├── agent/                      # ✅ THE BRAIN (Isolated)
│   ├── agent.py                # Graph entry point (build_graph)
│   ├── my_agent/               # LangGraph logic, nodes, tools
│   └── core/                   # Async DB & Redis clients
│
├── web/                        # 🆕 THE WEB SERVER
│   ├── __init__.py             # App Factory (create_app)
│   ├── app.py                  # Entry point
│   ├── config.py               # Centralized configuration
│   │
│   ├── blueprints/             # 🚦 ROUTERS (HTTP Logic)
│   │   ├── auth.py             # Auth routes
│   │   ├── chat.py             # Chat API endpoints
│   │   └── views.py            # HTML/Template rendering
│   │
│   └── services/               # 🧠 BRIDGE (Business Logic)
│       ├── chat_adapter.py     # 🔌 Sync/Async Adapter
│       └── auth_service.py     # Unified Authentication
│
├── templates/                  # Frontend HTML (Preserved)
└── static/                     # Frontend Assets (Preserved)
```

---

## 3. Key Components & Implementation Details

### A. The Adapter Layer (`web/services/chat_adapter.py`)
This is the most critical new component. It translates between the Web World (Flask/JSON) and the Agent World (LangGraph/State).

**Responsibilities:**
1.  **Sync-to-Async Bridge:** Uses `asgiref.sync.async_to_sync` or `asyncio.run()` to execute the async agent graph within synchronous Flask routes.
2.  **Data Formatting:** Converts LangGraph `State` (messages, current_question) into the specific JSON format expected by the frontend (`response`, `chip_options`).
3.  **UI Logic:** Determines when to show "Chips" (clickable options) based on the agent's current question type (MCQ, Boolean).

**Pseudo-Code:**
```python
def process_message(session_id, message):
    # 1. Prepare Input
    inputs = {"messages": [HumanMessage(content=message)]}
    config = {"configurable": {"thread_id": session_id}}
    
    # 2. Run Async Agent (Synchronously)
    final_state = async_to_sync(graph.ainvoke)(inputs, config)
    
    # 3. Format Response for Frontend
    return {
        "response": final_state["messages"][-1].content,
        "chip_options": _extract_chips(final_state),
        "ended": final_state["session_state"] == "FINISHED"
    }
```

### B. The Web Layer (`web/blueprints/`)
We will split `app.py` into smaller blueprints.
*   **`chat.py`**: Handles `/api/chat/*`. Minimal logic; delegates immediately to `chat_adapter`.
*   **`auth.py`**: Handles login/logout.
*   **`views.py`**: Renders `render_template("chat.html")`.

---

## 4. Frontend Integration
**Good News:** No changes are required to `templates/` or `static/`.
The frontend expects a specific JSON contract. As long as our **Adapter** outputs this contract, the frontend will not know the backend has changed.

**Contract:**
*   **Input:** `POST /api/chat/message` -> `{ "session_id": "...", "message": "..." }`
*   **Output:** 
    ```json
    {
      "success": true,
      "response": "Agent text response",
      "chip_options": { 
          "show_chips": true, 
          "options": ["Yes", "No"] 
      },
      "ended": false
    }
    ```

---

## 5. Migration Strategy (Strangler Fig Pattern)

We will not rewrite `app.py` overnight. We will migrate piece by piece.

1.  **Phase 1: Setup**
    *   Create `web/` directory structure.
    *   Create `web/services/chat_adapter.py` and connect it to `agent/`.
    *   Verify the adapter works with a unit test.

2.  **Phase 2: The Switch**
    *   Create `web/blueprints/chat.py`.
    *   In `app.py`, comment out the old `/api/chat/*` routes.
    *   Register the new `chat_bp` blueprint in `app.py`.
    *   **Test:** Run the frontend. It should now talk to the new agent seamlessly.

3.  **Phase 3: Cleanup**
    *   Move Auth and Views to blueprints.
    *   Delete `chat_engine.py`.
    *   Reduce `app.py` to just an entry point that imports the app factory.

---

## 6. Future Roadmap

1.  **Unified Authentication:**
    *   Currently, Auth is split. We will create `web/services/auth_service.py` to handle Firebase Admin initialization once. Both the Agent (for DB access) and Flask (for Session Auth) will import the DB client from here.

2.  **Configuration Management:**
    *   Use a single `.env` file but namespace variables.
    *   `OPENAI_API_KEY`: For legacy/fallback.
    *   `GOOGLE_API_KEY` / `GEMINI_API_KEY`: For the new agent.
    *   `LANGSMITH_*`: For tracing the new agent.

3.  **Async Optimization:**
    *   If load increases, we can swap the Flask server for **Quart** (which is API-compatible with Flask but native async) without changing the blueprint structure significantly.
