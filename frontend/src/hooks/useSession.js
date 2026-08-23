import { useState, useCallback, useRef } from 'react';
import { createSession, resumeSession } from '@/utils/api';

/**
 * useSession — manages the full lifecycle of a Paisaan chat session.
 *
 * State:
 *   messages   — [{role: 'assistant'|'user', content: string, id: string}]
 *   threadId   — current LangGraph thread_id (persisted to sessionStorage)
 *   userId     — current user id
 *   status     — 'idle' | 'loading' | 'interrupted' | 'complete' | 'error'
 *   error      — error message string or null
 *
 * Actions:
 *   startSession(userId?) — POST /session, set threadId, add first question
 *   sendAnswer(text)      — POST /session/{id}/resume, add reply + next question
 *   resetSession()        — clear everything and start fresh
 */
export function useSession() {
    const [messages, setMessages] = useState([]);
    const [threadId, setThreadId] = useState(
        () => sessionStorage.getItem('paisaan_thread_id') || null
    );
    const [userId, setUserId] = useState(
        () => sessionStorage.getItem('paisaan_user_id') || null
    );
    const [status, setStatus] = useState('idle');
    const [error, setError] = useState(null);

    // Guard against duplicate calls
    const loading = useRef(false);

    const addMessage = useCallback((role, content) => {
        setMessages(prev => [
            ...prev,
            { id: `${Date.now()}-${Math.random()}`, role, content },
        ]);
    }, []);

    /**
     * Start a new session. Calls POST /session and adds the first question.
     */
    const startSession = useCallback(async (existingUserId = null) => {
        if (loading.current) return;
        loading.current = true;
        setStatus('loading');
        setError(null);
        setMessages([]);

        try {
            const data = await createSession(existingUserId || userId);

            // Persist IDs so they survive a page refresh
            sessionStorage.setItem('paisaan_thread_id', data.thread_id);
            sessionStorage.setItem('paisaan_user_id', data.user_id);

            setThreadId(data.thread_id);
            setUserId(data.user_id);

            if (data.message) {
                addMessage('assistant', data.message);
            }

            setStatus(data.status);
        } catch (err) {
            setError(err.message || 'Failed to start session');
            setStatus('error');
        } finally {
            loading.current = false;
        }
    }, [userId, addMessage]);

    /**
     * Send the user's answer to the current interrupted question.
     * Adds user message, calls /resume, adds next assistant message.
     */
    const sendAnswer = useCallback(async (text) => {
        if (!threadId || loading.current || !text.trim()) return;
        loading.current = true;

        addMessage('user', text);
        setStatus('loading');
        setError(null);

        try {
            const data = await resumeSession(threadId, text);

            if (data.message) {
                addMessage('assistant', data.message);
            }

            setStatus(data.status);
        } catch (err) {
            setError(err.message || 'Something went wrong. Please try again.');
            setStatus('error');
            // Remove the optimistically added user message on error
            setMessages(prev => prev.slice(0, -1));
        } finally {
            loading.current = false;
        }
    }, [threadId, addMessage]);

    /**
     * Clear everything and reset to idle. User can start a new session.
     */
    const resetSession = useCallback(() => {
        sessionStorage.removeItem('paisaan_thread_id');
        sessionStorage.removeItem('paisaan_user_id');
        setMessages([]);
        setThreadId(null);
        setStatus('idle');
        setError(null);
    }, []);

    return {
        messages,
        threadId,
        userId,
        status,
        error,
        isLoading: status === 'loading',
        isComplete: status === 'complete',
        isInterrupted: status === 'interrupted',
        startSession,
        sendAnswer,
        resetSession,
    };
}
