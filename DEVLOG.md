# Paisaan Development Log

## August 23, 2026 — Phase 2: Market Data Tools
- Implemented the Mutual Fund NAV fetcher tool using `mfapi.in`.
- Implemented the Stock Price tool using `yfinance`, with auto `.NS` appending for Indian stocks.
- Implemented the Gold/Silver price fetcher using `yfinance` to fetch NSE Bullion ETF prices (`GOLDBEES.NS` and `SILVERBEES.NS`) as reliable, free, and correlated proxies for domestic bullion.
- Implemented the FD Rates fetcher tool using `duckduckgo-search` to aggregate live bank rates text snippets.
- Implemented the Market News search tool using `duckduckgo-search` to fetch the latest business news.
- All tools decorated with Langchain's `@tool` for easy agent consumption.
- Verified all 5 tools flawlessly fetch live data using isolated scratch scripts.

## August 23, 2026 — Phase 0: Skeleton & Architecture
- **LangGraph Checkpointer Architecture**: Implemented the mandatory architecture where FastAPI is stateless and LangGraph state is persisted across requests using `SqliteSaver`. Verified the `interrupt()` -> FastAPI -> `/resume` round-trip.
- **FastAPI Endpoints**: Created API routes for session management (`POST /session`, `POST /session/{id}/message`, `POST /session/{id}/resume`).
- **Database Schema**: Scaffolded SQLAlchemy ORM models and CRUD methods for `users`, `sessions`, `holdings`, and `transactions` (append-only audit log).
- **Frontend Skeleton**: Built the React frontend shell with a Chat interface, a placeholder Portfolio dashboard, and API utility functions.
- **Strict Config**: Enforced strict environment variable usage via `pydantic-settings` and `vite.config.js` to ensure the app relies purely on `.env` values.
- **CORS Fixes**: Resolved Cross-Origin resource sharing issues by dynamically mapping the `.env` frontend URL to accepted origins.

## August 23, 2026 — Phase 1: Intake Subgraph
- **Real LLM Intake Node** (`agent/nodes/intake.py`): LangGraph node uses the Gemini model (configured in `.env`, defaulting to `gemini-3.5-flash`) to dynamically generate questions for missing `Profile` fields. Self-loops until all 8 required fields (`age`, `income`, `expenses`, `existing_savings`, `dependents`, `investable_amount`, `risk_tolerance`, `goal`) are filled, then marks `intake_complete = True`.
- **Dynamic Model Configuration**: Extracted the hardcoded model name to a config setting `google_llm_model` in `config.py` (overridable via `GOOGLE_LLM_MODEL` in `.env`), allowing easy model upgrades without changing code.
- **Structured Output**: LLM answer parsing uses `Profile` from `state.py` directly via `with_structured_output()` — no duplicate model.
- **Self-looping Graph**: Updated `graph.py` with a conditional edge (`continue` → loop back to intake, `done` → END).
- **Session Lookup API** (`GET /session/{id}`): New endpoint fetches full session state from the checkpointer — messages, profile, and pending question. Returns `exists: false` if the thread ID is new.
- **Custom Thread ID**: `POST /session` now accepts an optional `thread_id`. Validated to have no spaces.
- **Landing Screen** (frontend): Chat page now shows a Session ID input before starting. User can enter any string (no spaces) to resume an existing session or start a new named one.
- **Full Session Restore**: If an existing thread ID is entered, the frontend fetches and displays the full message history and pending question from the checkpointer.
- **CSS Variable Compliance**: All frontend components (`Chat.jsx`, `Portfolio.jsx`, `Header.jsx`) updated to use `var(--token)` inline styles instead of hardcoded Tailwind color classes.
- **Session Loading & Restore Fixes**: Fixed a bug where entering a new custom thread ID would hang the page in a loading state due to `loading.current` locking `startSession` inside `loadSession`. Refactored `loadSession` to create sessions directly. Added a `useEffect` in `Chat.jsx` to automatically restore active sessions from `sessionStorage` on page refresh.
- **Conversational Intake Flow Optimization**: Refactored the `_generate_question` prompts to allow Paisaan to ask for multiple missing profile fields at once (e.g. 3-4 fields) instead of strictly one-by-one. If the user's input is ambiguous or incomplete, the model automatically detects it and asks precise clarifying questions.
