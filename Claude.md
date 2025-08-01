Bermuda MVP: Conversational Form Builder
Project Overview
Bermuda is a conversational alternative to Google Forms. Creators paste unstructured text "dumps" to infer forms via LLM (GPT-4o-mini). They edit/toggle elements and share links. Respondents chat with a natural, empathetic bot that collects data human-like. Backend extracts unstructured chats into structured responses. Focus on MVP: Core creation, chatting, dashboard. Leverage LLMs for robustness (prompts handle 90%+ edges). Anonymity for respondents; silent device/location collection for anti-abuse.
Key Goals:

* Maximize LLM use for inference, chatting, extraction (CoT, few-shots, self-critique).
* Anti-bias: Bot asks openly (no options listed); bucketize backend.
* Robust: Handle edges via prompts (e.g., off-topic "bananas" redirect).
* Scope: No analytics, multi-user, edits post-save.

Date Context: July 18, 2025 (for any time-sensitive elements).
Tech Stack

* Frontend: HTML/JS + Tailwind UI (for dashboard, form editor, chat interface). FingerprintJS for device_id.
* Backend: Python Flask (endpoints: /infer, /save, /chat_message, /extract, etc.).
* AI: OpenAI GPT-4o-mini + OpenAI Agents SDK (LLM chains for inference/extraction, Agent with tools for chat with Session memory).
* DB/Auth: Firebase (Firestore for forms/responses, Realtime DB for chat sync, Google SSO for creators).
* Deployment: Vercel

Modules and Requirements
Build progressively. Each module includes requirements and user stories. Implement module-by-module, testing edges after each.
Module 1: Infrastructure & Authentication
Requirements:

* Set up Firebase: Firestore, Realtime DB, Auth (Google SSO).
* Flask: /auth/google endpoint for login, token verification.
* Store/fetch profile in Firestore ('users' collection: email, user_id, created_at).
* Session middleware: Verify tokens for protected routes.
* Errors: Handle invalid tokens (401/403).

User Stories:

* As a creator, log in via Google to access dashboard.
* On login, auto-create/fetch profile.
* System prevents access on failed login.

Module 2: Form Inference
Requirements:

* /infer (POST): Input 'dump', LLMChain with GPT-4o-mini.
* Prompt: JSON output {'title', 'questions': [{text, type (text/multiple_choice/yes_no/number/rating), options, enabled: true}]}.
* CoT: Summarize intent, derive 5-10 questions, infer types, self-critique.
* Few-shots: 3-5 examples (e.g., color dump → multiple_choice).
* Demographics: Predefined toggleable list (age, gender, etc., with options like "Prefer not to say").
* Retry on invalid JSON (2x).

User Stories:

* Creator pastes dump, gets inferred JSON for editing.
* System infers logical types/options from dump.
* Demographics appear as editable/toggleable.

Module 3: Form Editing & Management
Requirements:

* Tailwind UI: Dashboard for dump input, /infer call, editable form (title, questions: edit text/type/options/toggles).
* Validation: Options required for multiple_choice; min 1 enabled question.
* Preview: JS mock chat (read-only simulation).
* /save_form: Generate form_id, store in Firestore.
* Share: Link generation (bermuda.app/form/{form_id}).

User Stories:

* Creator edits inferred form and toggles.
* Preview simulates respondent chat.
* Save validates and stores; share copies link.

Module 4: Respondent Chat Interface
Requirements:

* Tailwind chat UI: Load form via link, silent device_id (FingerprintJS) + location send.
* /chat_message: OpenAI Agents SDK (GPT-4o-mini, Session-based memory: last 10, Firebase sync).
* Agent Tools: 7 specialized tools (get_next_question, skip_current_question, validate_response, extract_multi_answers, redirect_conversation, clarify_response, end_conversation, save_response).
* Prompt: Natural (emojis/slang), one question/time, CoT for edges (off-topic: "bananas" redirect max 3, skips: [SKIP], conflicts: clarify/latest, vague: follow-up), [END] on complete.
* Anti-bias: Open questions; types guide backend only.
* Cap: 30 messages; timeout: 5 min.

DEVIATION FROM ORIGINAL PLAN: Switched from LangChain to OpenAI Agents SDK due to Vercel deployment size limits (250MB max). LangChain dependencies would exceed this limit. OpenAI Agents SDK is lightweight, official, and production-ready for our agentic chatbot needs.

User Stories:

* Respondent opens link, chats naturally; bot handles skips/vague.
* System collects device/location silently for session_id.

Module 5: Data Extraction & Storage
Requirements:

* /extract: LLMChain for transformation (CoT: type-specific bucketizing, e.g., no-fit → "other").
* Trigger: Partial every 5 messages (JS), full on [END]/timeout.
* Store: Firestore (session_id, data JSON, transcript, partial flag, device_id/location).
* Edges: Via prompt (conflicts: latest, skips: mark, vague: map).

User Stories:

* System extracts structured data from chat, saving partials.
* Handles no-fit/vague via backend bucketing.

Module 6: Dashboard & Viewing
Requirements:

* UI: List forms/responses, export JSON/CSV.
* /responses: Query by creator_id, flag partials/duplicates (device_id/location).
* Immutable post-save.

User Stories:

* Creator views responses, exports data, sees duplicate flags.

Module 7: Non-Functionals & Security
Requirements:

* Perf: <2s responses, rate-limit 50 msgs/hour (IP/device).
* Reliability: LLM retries (2x), JS network retries.
* Security: Prompt guards vs. injection, encryption.
* Accessibility: Tailwind ARIA.
* Privacy: Anonymous; internal device/location.

User Stories:

* System rate-limits abuse.
* Chats are reliable and private.

Module 8: Testing & Deployment
Requirements:

* Test top edges: Off-topic, skips, pre-answers, conflicts, vague, no-fit, abandonment, invalid types, multi-language, duplicates, abuse.
* Refine prompts for 90%+ accuracy.
* Deploy: Vercel with env vars.

User Stories:

* Developer tests edges end-to-end.
* MVP deploys scalably (<$50/month).

Top Edge Cases
Prioritize these (handle via prompts):

* Off-topic: "Bananas" redirect (max 3).
* Skips: [SKIP] tag.
* Pre/multi-answers: Parse in CoT.
* Conflicts: Prioritize latest.
* Vague: Follow-up, map in extraction.
* No-fit: Bucket to "other".
* Abandonment: Timeout partial save.
* Invalid types: Follow-up.
* Multi-language: Auto-detect/translate.
* Duplicates: Flag via device_id.
* Abuse: Rate-limit, guards.

Instructions for Claude

You are my expert dev team. Read this entire file. Build the MVP module-by-module as specified. For each module:

1. Generate full code (backend/frontend as needed).
2. Include tests for requirements/user stories.
3. Handle specified edges.
4. Ask for clarifications if ambiguous.
5. Iterate: After code, suggest improvements based on best practices.

Start with Module 1. Output in code blocks with explanations. Use terse, efficient code. Target robust, scalable MVP.

IMPORTANT: 
1. Keep updating progress.md with one liner terse yet informative updates
2. Before making updates, refer progress.md file to see what we've done / where we are so far
3. Please use wsgi based deployment for deploying on vercel. 
4. Use Firebase for SSO
5. Do not, I repeat, do not, never, hardcode or write custom css. Always use tailwind system default components which come off the shelf. You must ensure all components are in our design system and are not system default. We want custom dropdowns in our design styles and not system default. 
6. Use Phosphor icons for icons, accurately where required. 
7. Put the project on bermuda.vercel.app - which is the domain I've purchased for this project.
8. Stack: Python Flask HTML CSS React (Simple lightweight)
9. Always test the experience to ensure what you ship works.
10. Don't forget to use virtual environment for python work. 
11. Deployment: Vercel - bermuda (make new project in vercel), github: bermuda (make new repo)
12. Use my cli for vercel (npx vercel) and github cli. I'm logged in everywhere.
13. For edge cases in chat, use @EdgeCases.md 
14. For designs while making the frontend, refer figma links in @DesignLinks.md and use your MCP. 
15. IMPORTANT: CHATBOT MUST HAVE AGENTIC FLOW i.e. CHATBOT MUST BE AGENTIC WITH TOOL IMPLEMENTATION. RESEARCH ON WEB FIRST AND ONLY THEN IMPLEMENT THIS PART. IT SHOULD AUTO_HANDLE all edge cases and use cases and naturally. 