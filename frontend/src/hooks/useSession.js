import { useState, useCallback, useRef } from 'react';
import { createSession, resumeSession, getSessionState } from '@/utils/api';

export function useSession() {
    const [messages, setMessages] = useState([]);
    const [threadId, setThreadId] = useState(
        () => sessionStorage.getItem('paisaan_thread_id') || null
    );
    const [userId, setUserId] = useState(
        () => sessionStorage.getItem('paisaan_user_id') || null
    );
    const [profile, setProfile] = useState({});
    const [status, setStatus] = useState('idle');
    const [error, setError] = useState(null);
    const [payload, setPayload] = useState(null);

    const loading = useRef(false);

    const addMessage = useCallback((role, content) => {
        setMessages(prev => [...prev, { id: `${Date.now()}-${Math.random()}`, role, content }]);
    }, []);

    const _persist = (tid, uid) => {
        sessionStorage.setItem('paisaan_thread_id', tid);
        sessionStorage.setItem('paisaan_user_id', uid);
    };

    const startSession = useCallback(async (customThreadId = null) => {
        if (loading.current) return;
        loading.current = true;
        setStatus('loading');
        setError(null);
        setMessages([]);
        setProfile({});
        setPayload(null);

        try {
            const data = await createSession(userId, customThreadId || null);
            _persist(data.thread_id, data.user_id);
            setThreadId(data.thread_id);
            setUserId(data.user_id);
            if (data.message) addMessage('assistant', data.message);
            setStatus(data.status);
            setPayload(data.payload);
        } catch (err) {
            setError(err.message || 'Failed to start session');
            setStatus('error');
        } finally {
            loading.current = false;
        }
    }, [userId, addMessage]);

    const loadSession = useCallback(async (customThreadId) => {
        if (loading.current || !customThreadId) return;
        loading.current = true;
        setStatus('loading');
        setError(null);
        setMessages([]);
        setProfile({});
        setPayload(null);

        try {
            const data = await getSessionState(customThreadId);

            if (!data.exists) {
                const startData = await createSession(userId, customThreadId);
                _persist(startData.thread_id, startData.user_id);
                setThreadId(startData.thread_id);
                setUserId(startData.user_id);
                if (startData.message) addMessage('assistant', startData.message);
                setStatus(startData.status);
                setPayload(startData.payload);
                return;
            }

            _persist(customThreadId, data.user_id || '');
            setThreadId(customThreadId);
            setUserId(data.user_id);

            const restored = (data.messages || []).map((m, i) => {
                const role = m.role || (m.type === 'ai' ? 'assistant' : m.type === 'human' ? 'user' : m.type);
                return {
                    id: `restored-${i}`,
                    role: role,
                    content: m.content,
                };
            });

            if (data.tool_calls && data.tool_calls.length > 0) {
                for (let i = restored.length - 1; i >= 0; i--) {
                    if (restored[i].role === 'assistant') {
                        restored[i].toolCalls = data.tool_calls;
                        break;
                    }
                }
            }

            if (data.pending_question) {
                const alreadyPresent = restored.some(
                    m => m.role === 'assistant' && m.content === data.pending_question.text
                );
                if (!alreadyPresent) {
                    restored.push({
                        id: `restored-pending`,
                        role: 'assistant',
                        content: data.pending_question.text,
                    });
                }
            }

            setMessages(restored);
            setProfile(data.profile || {});
            setStatus(data.status || 'interrupted');
            setPayload(data.pending_question || null);
        } catch (err) {
            setError(err.message || 'Failed to load session');
            setStatus('error');
        } finally {
            loading.current = false;
        }
    }, [userId, addMessage]);

    const sendAnswer = useCallback(async (text) => {
        if (!threadId || loading.current || !text.trim()) return;
        loading.current = true;
        addMessage('user', text);
        setStatus('loading');
        setError(null);
        setPayload(null);

        try {
            const data = await resumeSession(threadId, text);
            if (data.message) {
                setMessages(prev => [...prev, {
                    id: `${Date.now()}-${Math.random()}`,
                    role: 'assistant',
                    content: data.message,
                    toolCalls: data.tool_calls || [],
                }]);
            }
            setStatus(data.status);
            setPayload(data.payload);
        } catch (err) {
            setError(err.message || 'Something went wrong. Please try again.');
            setStatus('error');
            setMessages(prev => prev.slice(0, -1));
        } finally {
            loading.current = false;
        }
    }, [threadId, addMessage]);

    const resetSession = useCallback(() => {
        sessionStorage.removeItem('paisaan_thread_id');
        sessionStorage.removeItem('paisaan_user_id');
        setMessages([]);
        setThreadId(null);
        setUserId(null);
        setProfile({});
        setStatus('idle');
        setError(null);
        setPayload(null);
    }, []);

    return {
        messages,
        threadId,
        userId,
        profile,
        status,
        error,
        payload,
        isLoading: status === 'loading',
        isComplete: status === 'complete',
        isInterrupted: status === 'interrupted',
        startSession,
        loadSession,
        sendAnswer,
        resetSession,
    };
}
