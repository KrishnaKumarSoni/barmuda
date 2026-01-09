# Barmuda Migration & Refactoring Plan

## 🎯 Objective
Migrate the monolithic `app.py` (3000+ lines) into a modular Flask architecture (Modular Monolith) and replace the legacy `chat_engine.py` with the next-gen **LangGraph** agent located in `/agent`.

---

## 🏗️ Target Architecture
```text
/barmuda
├── agent/                  # THE BRAIN (Isolated LangGraph logic)
├── web/                    # THE WEB SERVER (Flask App Factory)
│   ├── blueprints/         # Routes (Auth, API, Views, Billing)
│   ├── services/           # Business Logic (Chat Adapter, Auth Service)
│   ├── extensions.py       # Shared instances (DB, Firebase, etc.)
│   └── __init__.py         # App Factory
├── templates/              # UI (Preserved)
└── app.py                  # Entry Point (Minimal)
```

---

## 🚀 Phase 1: Web Layer Refactor (Current Priority)
**Goal:** Break the monolith without changing business logic.

- [ ] **Step 1: Scaffold Directory Structure**
  - Create `web/`, `web/blueprints/`, `web/services/`.
  - Create `web/extensions.py` to hold global objects (Firestore client, etc.).
- [ ] **Step 2: App Factory Implementation**
  - Create `web/__init__.py` with `create_app()`.
  - Create `web/config.py` for environment variables.
- [ ] **Step 3: Blueprint Extraction**
  - Extract Auth routes to `web/blueprints/auth.py`.
  - Extract View routes to `web/blueprints/views.py`.
  - Extract Billing routes to `web/blueprints/billing.py`.
  - Move legacy chat logic to `web/blueprints/legacy_chat.py`.
- [ ] **Step 4: Cleanup app.py**
  - Reduce `app.py` to a 5-line entry point.

---

## 🔌 Phase 2: The Agent Bridge (Integration)
**Goal:** Connect the new Flask structure to the LangGraph agent.

- [ ] **Step 1: Chat Adapter Service**
  - Create `web/services/chat_adapter.py`.
  - Implement the Sync-to-Async bridge to run LangGraph.
  - Map LangGraph state to existing Frontend JSON contracts.
- [ ] **Step 2: V2 Chat Endpoint**
  - Create `web/blueprints/chat_v2.py`.
  - Verify parity with legacy chat using a test form.

---

## 🏁 Phase 3: The Final Switch
**Goal:** Full cutover and decommissioning.

- [ ] **Step 1: Route Redirection**
  - Point Frontend JS or Backend routes to the new Agent.
- [ ] **Step 2: Legacy Deletion**
  - Delete `chat_engine.py`.
  - Remove legacy chat blueprints.
  - Final cleanup of unused dependencies.

---

## 📝 Progress Log
- **2026-01-09:** Plan finalized and documented.
