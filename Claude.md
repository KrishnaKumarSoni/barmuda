Barmuda MVP: Conversational Form Builder
Project Overview
Barmuda is a conversational alternative to Google Forms. Creators paste unstructured text "dumps" to infer forms via LLM (GPT-4o-mini). They edit/toggle elements and share links. Respondents chat with a natural, empathetic bot that collects data human-like. Backend extracts unstructured chats into structured responses. Focus on MVP: Core creation, chatting, dashboard. Leverage LLMs for robustness (prompts handle 90%+ edges). Anonymity for respondents; silent device/location collection for anti-abuse.
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

Module 2: Form Inference (ENHANCED)
Requirements:

* /infer (POST): Input 'dump', LLMChain with GPT-4o-mini.
* **AUTO-SAVE**: Generated forms are immediately saved as active: false (inactive) to prevent data loss.
* **Template System**: 12 pre-built form templates with icons for common use cases (Customer Feedback, Employee Survey, Market Research, etc.).
* Prompt: JSON output {'title', 'questions': [{text, type (text/multiple_choice/yes_no/number/rating), options, enabled: true}]}.
* CoT: Summarize intent, derive 5-10 questions, infer types, self-critique.
* Few-shots: 3-5 examples (e.g., color dump → multiple_choice).
* Demographics: Predefined toggleable list (age, gender, etc., with options like "Prefer not to say").
* Retry on invalid JSON (2x).

User Stories:

* Creator pastes dump OR selects template, gets inferred JSON for editing.
* **Auto-save prevents data loss** - forms persist even if user navigates away.
* System infers logical types/options from dump.
* Demographics appear as editable/toggleable with proper toggle hierarchy.

Module 3: Form Editing & Management (ENHANCED)
Requirements:

* **URL-based Loading**: Edit form loads by form_id from URL parameter (/edit-form?id=form_id).
* **Responsive Navigation**: Reusable nav component with mobile support and proper floating design.
* Tailwind UI: Dashboard for dump input, /infer call, editable form (title, questions: edit text/type/options/toggles).
* **Demographics Logic**: Main toggle controls entire section; individual toggles only work when section is enabled.
* Validation: Options required for multiple_choice; min 1 enabled question.
* Preview: JS mock chat (read-only simulation).
* **Save & Launch**: Updates form to active: true and generates share_url.
* Share: Link generation (barmuda.vercel.app/form/{form_id}).

User Stories:

* Creator edits inferred form and toggles with intuitive UX.
* **Seamless workflow**: Can navigate away and return to continue editing.
* Preview simulates respondent chat accurately.
* Save & Launch activates form for response collection.

Module 4: Respondent Chat Interface (ENHANCED)
Requirements:

* **Active/Inactive Control**: Only active forms accept responses. Inactive forms show "Survey Not Available" message.
* **Response Protection**: /form/<form_id> and /api/chat/start validate form.active before allowing responses.
* Tailwind chat UI: Load form via link, silent device_id (FingerprintJS) + location send.
* /chat_message: OpenAI Agents SDK (GPT-4o-mini, Session-based memory: last 10, Firebase sync).
* Agent Tools: 7 specialized tools (get_next_question, skip_current_question, validate_response, extract_multi_answers, redirect_conversation, clarify_response, end_conversation, save_response).
* Prompt: Natural (emojis/slang), one question/time, CoT for edges (off-topic: "bananas" redirect max 3, skips: [SKIP], conflicts: clarify/latest, vague: follow-up), [END] on complete.
* Anti-bias: Open questions; types guide backend only.
* Cap: 30 messages; timeout: 5 min.

DEVIATION FROM ORIGINAL PLAN: Switched from LangChain to OpenAI Agents SDK due to Vercel deployment size limits (250MB max). LangChain dependencies would exceed this limit. OpenAI Agents SDK is lightweight, official, and production-ready for our agentic chatbot needs.

User Stories:

* **Toggle Control**: Form owners can instantly pause/resume response collection.
* Respondent opens link, chats naturally; bot handles skips/vague.
* **Inactive forms are blocked** - shared links stop working when toggled off.
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

Module 6: Dashboard & Viewing (ENHANCED)
Requirements:

* **Unified Dashboard**: Shows ALL forms (both active and inactive) with visual distinction.
* **Active/Inactive Toggle**: Toggle forms on/off to control response collection in real-time.
* **Complete Action Set**: All forms get full icon buttons (edit, delete, test, share, responses).
* **Auto-saved Forms**: Dashboard displays inactive forms generated but not yet launched.


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

## Current Implementation Status (January 2025)

**✅ COMPLETED MODULES:**

**Module 1: Infrastructure & Authentication** - DONE
- Firebase SSO with Google authentication
- Session-based auth middleware
- Protected routes with proper error handling

**Module 2: Form Inference (Enhanced)** - DONE  
- Auto-save generated forms as inactive to prevent data loss
- 12 template widgets for common use cases (Customer Feedback, Employee Survey, etc.)
- LLM-powered form generation with CoT and few-shots
- Comprehensive input validation and error handling

**Module 3: Form Editing & Management (Enhanced)** - DONE
- URL-based form loading (/edit-form?id=form_id)
- Responsive navigation component with mobile support
- Fixed demographics toggle logic with proper hierarchy
- Preview functionality with mock chat simulation
- Save & Launch activates forms (active: true)

**Module 4: Respondent Chat Interface (Enhanced)** - DONE
- Active/inactive response control system
- Protected endpoints prevent responses to inactive forms
- OpenAI Agents SDK with 7 specialized tools
- Natural conversation flow with proper edge case handling
- Session management with device fingerprinting

**Module 5: Data Extraction & Storage** - DONE
- Structured data extraction from chat transcripts
- Partial saves every 5 messages
- Response storage with metadata (device_id, location, etc.)

**Module 6: Dashboard & Viewing (Enhanced)** - DONE
- Unified dashboard showing all forms (active and inactive)
- Real-time active/inactive toggle for response control
- Complete action buttons for all forms
- Response viewing and export functionality

**Module 7: Non-Functionals & Security** - DONE
- Rate limiting and abuse protection
- Input validation and sanitization
- Responsive design with Tailwind
- Performance optimization

**Module 8: Testing & Deployment** - DONE
- Deployed on barmuda.vercel.app
- Edge case handling via prompts
- End-to-end testing completed

**Module 9: Professional Embed Widget System** - DONE
- Floating Action Button (FAB) widget for website integration
- Modal overlay chat interface (no iframe conflicts)
- Configurable positioning (bottom-left/right) and brand colors
- "Powered by barmuda.in" branding integration
- Mobile-responsive design with smooth animations
- Dashboard embed modal with live preview and customization
- Single-script integration (no complex setup required)
- Professional UX matching industry standards (Intercom/Drift style)

## Key Architectural Decisions & Enhancements

**Auto-Save System:**
- Generated forms immediately saved as `active: false`
- Prevents data loss when users navigate away
- Seamless editing workflow with URL-based loading

**Response Control System:**
- Only active forms (`active: true`) can receive responses
- Inactive forms show "Survey Not Available" message
- Toggle provides instant control over response collection
- Shared links stop working when forms are paused

**Template System:**
- 12 pre-built templates for common use cases
- Icon-based selection with Phosphor icons
- Reduces form creation time and improves UX

**Enhanced UX:**
- Responsive navigation with mobile support
- Proper demographics toggle hierarchy
- Visual feedback for form states
- Intuitive dashboard with complete functionality

**Professional Embed Widget:**
- FAB widget replaces iframe approach (no CSP/CORS conflicts)
- `/widget.js` route serves JavaScript with proper CORS headers
- Dynamic modal overlay with full chat functionality
- Configurable branding and positioning options
- Industry-standard installation (single script tag)
- Mobile-first responsive design with animations
- Non-intrusive floating button (doesn't disrupt page layout)

## Instructions for Claude

**Current Status:** MVP is COMPLETE and DEPLOYED at barmuda.vercel.app

**Architecture Guidelines:**
1. Maintain auto-save functionality for data persistence
2. Respect active/inactive response control system
3. Use Tailwind system components (never custom CSS)
4. Leverage Phosphor icons consistently
5. Maintain responsive design principles
6. Follow established patterns in codebase
7. Ensure embed widget compatibility across all form features
8. Test widget functionality on different domains and devices

**For Future Enhancements:**
1. Follow existing code patterns and architecture
2. Test active/inactive response control for any new features
3. Maintain compatibility with auto-save system
4. Use TodoWrite tool for task management
5. Update this file for significant changes

**Deployment:**
- Production: barmuda.vercel.app (Vercel)
- Repository: github.com/KrishnaKumarSoni/bermuda
- Stack: Python Flask + HTML/CSS/JS + Tailwind + Firebase

**Embed Widget Usage:**
```html
<script>
(function() {
    var script = document.createElement('script');
    script.src = 'https://barmuda.vercel.app/widget.js';
    script.setAttribute('data-form-id', 'YOUR_FORM_ID');
    script.setAttribute('data-position', 'bottom-right'); // or 'bottom-left'
    script.setAttribute('data-color', '#cc5500'); // custom brand color
    document.head.appendChild(script);
})();
</script>
```

**Key Files:**
- `/static/widget.js` - Main widget JavaScript with FAB and modal
- `/templates/embed.html` - Fallback iframe template (legacy)
- `/templates/dashboard.html` - Updated with embed modal and customization
- `app.py` - Added `/widget.js` route with CORS headers

**Edge Cases:** Refer to @EdgeCases.md for chat conversation handling
**Design System:** Refer to @DesignLinks.md for Figma design references 

* Memorise this please as a backlog item