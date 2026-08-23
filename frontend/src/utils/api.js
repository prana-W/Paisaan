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
        throw new ApiError(errData?.detail || `HTTP ${res.status}`, res.status, errData);
    }

    return res.json();
}

export async function getSessions(userId = null) {
    const query = userId ? `?user_id=${userId}` : '';
    return request(`/sessions${query}`);
}

export async function getSessionState(threadId) {
    return request(`/session/${threadId}`);
}

export async function createSession(userId = null, threadId = null) {
    return request('/session', {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, thread_id: threadId }),
    });
}

export async function resumeSession(threadId, answer) {
    return request(`/session/${threadId}/resume`, {
        method: 'POST',
        body: JSON.stringify({ answer }),
    });
}

export async function sendMessage(threadId, content) {
    return request(`/session/${threadId}/message`, {
        method: 'POST',
        body: JSON.stringify({ content }),
    });
}

export async function getPortfolio(userId) {
    return request(`/portfolio/${userId}`);
}

export async function checkHealth() {
    return fetch(`${BASE_URL.replace('/api/v1', '')}/health`).then(r => r.json());
}
