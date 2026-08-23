/**
 * API utility — all calls to the Paisaan backend go through here.
 * Base URL is read from VITE_API_URL env var.
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:9000/api/v1';

class ApiError extends Error {
    constructor(message, status, data) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.data = data;
    }
}

async function request(path, options = {}) {
    const url = `${BASE_URL}${path}`;
    const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });

    if (!res.ok) {
        let errData;
        try { errData = await res.json(); } catch { errData = {}; }
        throw new ApiError(
            errData?.detail || `HTTP ${res.status}`,
            res.status,
            errData,
        );
    }

    return res.json();
}

// ── Session endpoints ─────────────────────────────────────────────────────────

/**
 * POST /session
 * Creates a new session and starts the agent graph.
 * @param {string|null} userId - existing user id, or null for anonymous
 * @returns {Promise<{thread_id, user_id, status, message, payload}>}
 */
export async function createSession(userId = null) {
    return request('/session', {
        method: 'POST',
        body: JSON.stringify({ user_id: userId }),
    });
}

/**
 * POST /session/{id}/resume
 * Resume a paused (interrupted) graph with the user's answer.
 * This works even after a tab close — state is in the checkpointer DB.
 * @param {string} threadId
 * @param {string} answer - the user's reply to the interrupted question
 * @returns {Promise<{thread_id, status, message, payload}>}
 */
export async function resumeSession(threadId, answer) {
    return request(`/session/${threadId}/resume`, {
        method: 'POST',
        body: JSON.stringify({ answer }),
    });
}

/**
 * POST /session/{id}/message
 * Send a chat message during intake.
 * @param {string} threadId
 * @param {string} content
 * @returns {Promise<{thread_id, status, message, payload}>}
 */
export async function sendMessage(threadId, content) {
    return request(`/session/${threadId}/message`, {
        method: 'POST',
        body: JSON.stringify({ content }),
    });
}

/**
 * GET /portfolio/{userId}
 * Get portfolio with live valuations (Phase 7).
 * @param {string} userId
 */
export async function getPortfolio(userId) {
    return request(`/portfolio/${userId}`);
}

/**
 * GET /health
 * Check if the server is up.
 */
export async function checkHealth() {
    return fetch(`${BASE_URL.replace('/api/v1', '')}/health`).then(r => r.json());
}
