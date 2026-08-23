# Paisaan Development Log

## August 23, 2026 — Phase 0: Skeleton & Architecture
- **LangGraph Checkpointer Architecture**: Implemented the mandatory architecture where FastAPI is stateless and LangGraph state is persisted across requests using `SqliteSaver`. Verified the `interrupt()` -> FastAPI -> `/resume` round-trip.
- **FastAPI Endpoints**: Created API routes for session management (`POST /session`, `POST /session/{id}/message`, `POST /session/{id}/resume`).
- **Database Schema**: Scaffolded SQLAlchemy ORM models and CRUD methods for `users`, `sessions`, `holdings`, and `transactions` (append-only audit log).
- **Frontend Skeleton**: Built the React frontend shell with a Chat interface, a placeholder Portfolio dashboard, and API utility functions.
- **Strict Config**: Enforced strict environment variable usage via `pydantic-settings` and `vite.config.js` to ensure the app relies purely on `.env` values.
- **CORS Fixes**: Resolved Cross-Origin resource sharing issues by dynamically mapping the `.env` frontend URL to accepted origins.
