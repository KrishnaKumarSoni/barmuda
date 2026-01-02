# Autonomous Survey Agent: Business & Operations Reference (v2)

This document provides a clear, high-level explanation of the Autonomous Survey Agent's components, logic, and architecture. It is intended for a non-technical audience and reflects the latest codebase.

## 1. Core Architecture: A Middleware-Driven Agent

The agent's intelligence is built on **LangGraph**, a framework for creating stateful, multi-step applications. The biggest change from the previous design is the use of **Middleware**, which are special components that intercept and modify the agent's behavior before or after it "thinks." This creates a much more robust and predictable system.

-   **`bootstrap_session_middleware`**: When a new conversation starts, this middleware immediately takes control. It bypasses the agent's brain (the LLM) and forces the `load_survey` tool to run. This ensures every session starts correctly without relying on the LLM to remember to do it.
-   **`survey_persona_prompt` (Dynamic Prompt)**: This is the agent's "inner voice." Before the LLM runs, this middleware dynamically builds a detailed set of instructions (a "prompt"). It injects the agent's assigned `persona`, the list of remaining questions, and the specific question the agent should be asking right now (the `Current Focus`), including any validation rules.
-   **`ContextEditingMiddleware`**: To keep the conversation history from becoming too long and expensive, this middleware automatically cleans up old tool interactions, keeping the agent focused on the recent parts of the conversation.
-   **`FrustrationGuardMiddleware` (Disabled)**: A "safety net" was built to detect if a user is struggling to answer a question. After three consecutive errors, it would force the agent to offer to skip the question. This feature is currently turned off but can be enabled easily.

## 2. The Agent's "Memory" (AgentState)

To function correctly, the agent needs to remember several key pieces of information. This "memory," which we call the `AgentState`, is updated continuously.

-   **`messages`**: A complete history of the conversation.
-   **`session_id`**: A unique identifier for this specific conversation.
-   **`form_id`**: The identifier for the survey being conducted (e.g., "form_2").
-   **`session_state`**: The overall status of the survey: "ONGOING", "FINISHED", or "TERMINATED".
-   **`persona`**: The personality the agent should adopt, loaded from the survey's configuration file.
-   **`questions`**: The full list of all possible questions for the current survey.
-   **`responses`**: A **dictionary** (not a list) that tracks the live status of each question, where each question key maps to an object containing its `status` ("UNASKED", "ASKED", "ANSWERED", "SKIPPED") and `value`.
-   **`current_question_key`**: The specific question the agent is currently focused on.
-   **`current_question_status`**: Indicates if the agent has just "ASKED" a new question or is "CLARIFYING" the user's previous answer.

## 3. The Agent's "Toolkit"

The agent's "brain" (the LLM) uses a set of approved "tools" to perform actions. The available tools have been significantly updated for efficiency and power.

| Tool Name | Description From Codebase | What the Brain Provides | State Changes |
| :--- | :--- | :--- | :--- |
| **`load_survey`** | Bootstraps the session. Loads the form schema and any existing answers. | Nothing. This is triggered automatically by middleware at the start. | Populates `questions`, `responses`, `persona`, and sets the first question to ask. |
| **`save_answer`** | Validates and saves a list of one or more answers. If the current question is answered correctly, **it automatically finds the next question to ask.** | A list of answers, e.g., `[{"question_key": "displayName", "value": "test"}]`. | Updates the `responses` dictionary with the new answer(s) and status. If successful, updates `current_question_key` to the next unasked question. |
| **`update_question_state`**| Updates the current question's state to CLARIFYING or SKIPPED. | The `target_question_key` and a `new_status` ("CLARIFYING" or "SKIPPED"). | If CLARIFYING, it keeps the focus on the current question. If SKIPPED, it marks the question as skipped **and moves to the next one.** |
| **`end_survey`** | Ends the survey session. | A `reason` for ending the survey. | Sets the `session_state` to "FINISHED". |
| **`get_all_questions`** | Retrieves a full summary of the survey questions and their current status. | Nothing. | None. It reads the state to provide a summary. |

*Note: A `skip_current_question` tool also exists, which only marks a question as skipped without moving to the next one. However, it is not currently provided to the agent.*

## 4. The Agent's "Core Instructions" (Dynamic System Prompt)

This is the master prompt that governs the agent's behavior. It is now dynamically generated. It starts with a base template and then has real-time information injected by the `survey_persona_prompt` middleware.

**Base Prompt (`BASE_PERSONA`):**
> ## 1. IDENTITY & CORE DIRECTIVE
> You are a charismatic, curious, and attentive interviewer. Your goal is to have a natural, flowing conversation while covertly gathering specific data points.
>
> **THE GOLDEN RULE:** The user must feel like they are chatting with a person, not filling out a form.
> - **Never** mention "systems," "databases," "records," "logging," or "validation."
> - **Never** give "heads-up" warnings about format rules (e.g., do not say "it needs to be one word" *before* they answer).
> - **Never** list options robotically (e.g., "Choose one of: A, B, or C"). Instead, weave them into the conversation naturally.
>
> ## 2. CONVERSATION STRATEGY: "THE WEAVE"
> Construct every response using this 3-step conversational loop:
>
> 1.  **Validate (The Acknowledgment):** React specifically to what the user just said with empathy or interest. Make them feel heard.
> 2.  **Bridge (The Pivot):** Create a smooth, logical transition from their last topic to the new topic.
> 3.  **Ask (The Inquiry):** Ask the question from `Current Focus` in a natural, spoken style.
>
> ## 3. HANDLING DATA & CONSTRAINTS
> The `SURVEY CONTEXT` below contains **Internal Rules** for your reference only.
>
> *   **Handling "Validation" Fields:**
>     *   **Proactive (Before Answer):** IGNORE the validation rule. Ask the question simply and broadly.
>     *   **Reactive (After Invalid Answer):** If the user provides an answer that violates the rule, DO NOT cite the rule. Instead, play it off as a social misunderstanding or a personal quirk.
>         *   *Bad:* "Error. The system allows max 30 characters."
>         *   *Good:* "That's a great story, but I want to fit your name on a tiny badge—what's a shorter version I can use?"
>
> * **Multi-Slot Extraction:** Listen actively. If the user provides information for *multiple* fields in a single turn (even for future questions), immediately call `save_answer` for all relevant keys.
>
> ## 4. EXECUTION PROTOCOL
> 1.  **Check Context:** Look at `Current Focus`. This is your topic.
> 2.  **Check History:** Did the user just speak? If so, react to it first.
> 3.  **Speak:** Generate your response using "The Weave." Keep it concise (under 2 sentences usually).

**Dynamically Injected Context (Example):**
```
--- SURVEY CONTEXT ---
Remaining question keys:
  - yearsOfExperience
  - primaryRole [Choices: Backend / Systems Engineer (backend), Frontend / UX Engineer (frontend), ML / AI Engineer (ml), AI Researcher (research)]
  ...

Current Focus: 'displayName'
  - Question: "What name should we display on leaderboards?"
  - Validation: Must be a single word with no spaces. Max length 30 characters.
```

## 5. High-Level Form Schema (`form_2.json`)

The survey's structure is defined in an external JSON file.

- **Title**: Agentic Systems Hackathon — Comprehensive Registration
- **Description**: This form helps us understand how you think, build, and reason about real-world agentic AI systems.
- **Agent Persona**: "be high-energy, casual, and use slang"
- **Questions**: The file defines each question's `key`, `text`, `type` (text, mcq, rating, etc.), and `validationRule`.

## 6. Detailed Interaction Flow

This new flow shows how the middleware-driven system works.

**Turn 1: Starting the Conversation**

1.  **User to System**: A user starts a new session.
2.  **System to Middleware**: The system activates the agent. The `bootstrap_session_middleware` detects that this is a new session because the `responses` dictionary in the state is empty.
3.  **Middleware Bypasses LLM**: The middleware **stops** the agent from thinking and instead injects a command to run the `load_survey` tool.
4.  **Tool Execution**:
    *   `load_survey` runs. It reads `form_2.json`.
    *   It populates the agent's memory (`AgentState`) with the questions, persona, and an empty response map.
    *   It identifies the first question ("displayName") and sets it as the `current_question_key`.
5.  **Middleware to LLM**: Control is now handed back to the agent's main loop. The `survey_persona_prompt` middleware builds the dynamic prompt, telling the LLM its persona and that its current focus is "displayName".
6.  **LLM to User**: The LLM, following its instructions, adopts the persona ("high-energy, casual") and asks the first question conversationally: "Yo, let's get this rolling! What name should we slap on the leaderboards?"

**Turn 2: Receiving an Answer**

1.  **User to LLM**: The user types their name, "Devansh", and hits send.
2.  **LLM's Thought Process**: The LLM sees the incoming message "Devansh". It looks at its dynamic prompt, which confirms the `Current Focus` is "displayName". It correctly decides to use the `save_answer` tool.
3.  **Agent Uses a Tool**: It calls `save_answer` with `[{"question_key": "displayName", "value": "Devansh"}]`.
4.  **Tool Execution**:
    *   The `save_answer` tool receives the data. It validates that "Devansh" is a valid name.
    *   It updates the database and the agent's `responses` memory, marking "displayName" as "ANSWERED".
    *   Crucially, it then automatically looks for the next unanswered question. It finds "yearsOfExperience".
    *   The tool finishes by updating the agent's memory, setting the `current_question_key` to "yearsOfExperience".
5.  **LLM to User**: The agent loop runs again. The dynamic prompt is rebuilt, now showing the `Current Focus` is "yearsOfExperience". The LLM, following "The Weave" strategy, first acknowledges the previous answer and then asks the new question: "Got it, Devansh! Solid name. Aight, next up: how many years have you been coding for real?" and the cycle continues.




Add form context metadata in form.json (what is the survey about?)
Add "others" in mcq questions
Remove MCQ options in llm context - directly send to frontend (Handle in frontend)
fix skip question tool
connect firestore - implement restore session
concurrency - async - redis
Gracefully end survey and prevent further responses


* Generate form system prompt
* Deploy in prod
* update question state not working


 ☐ Build Production API with FastAPI: Create a new `server.py` to define your API endpoints using FastAPI. This will replace
   the `langgraph dev` server for production use.
 ☐ Containerize the Application: Create a `Dockerfile` that sets up the environment, installs dependencies from
   `requirements.txt`, and specifies the `gunicorn` command to run your FastAPI server.
 ☐ Deploy to a Scalable Platform: Deploy your container image to a service like Google Cloud Run, ensuring the service is
   located in the same region as your Firestore database to minimize latency.
 ☐ Externalize All Configuration: Ensure no secrets or project IDs are hardcoded. Configure your production service to pass
   all settings via secure environment variables.
 ☐ Monitor and Optimize (Post-Launch): After deployment, analyze performance and cost metrics. Only if justified by data,
   consider implementing a caching layer like Redis to further reduce latency and cost.

   1. API Interface (The Next Step):
       * You need a server.py to expose this graph.
       * Decision: Will you use a simple REST endpoint (POST /chat) that returns the full response, or a Streaming endpoint
         (SSE/Websockets) that streams the agent's thoughts token-by-token? (Streaming is better for UX but slightly more
         complex to implement).

   2. Hosting Location:
       * You are heavily invested in Google Cloud (Firestore, Vertex AI).
       * Decision: Confirming Google Cloud Run as the deployment target is practically a no-brainer. It solves the SSL, load
         balancing, and container orchestration for you.

   3. Authentication:
       * Your API currently has no "guard" at the door.
       * Decision: How will your frontend authenticate with your backend? Simple API Key? JWT tokens? Firebase Auth? (Firebase
         Auth is easiest if you're already using Firestore).

   4. Error Handling Strategy:
       * What happens if Firestore times out or the LLM fails?
       * Decision: You need to decide on a retry policy (already partially handled by LangGraph) and a fallback response to
         the user ("I'm having trouble thinking right now...").