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

    const loading = useRef(false);

    const addMessage = useCallback((role, content) => {
        const strContent = typeof content === 'string'
            ? content
            : Array.isArray(content)
                ? content.map(b => (typeof b === 'string' ? b : (b?.text ?? ''))).join('')
                : typeof content === 'object' && content !== null
                    ? (content.text || JSON.stringify(content))
                    : String(content ?? '');
        setMessages(prev => [...prev, { id: `${Date.now()}-${Math.random()}`, role, content: strContent }]);
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

        try {
            const data = await createSession(userId, customThreadId || null);
            _persist(data.thread_id, data.user_id);
            setThreadId(data.thread_id);
            setUserId(data.user_id);
            if (data.message) addMessage('assistant', data.message);
            setStatus(data.status);
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

        try {
            const data = await getSessionState(customThreadId);

            if (!data.exists) {
                const startData = await createSession(userId, customThreadId);
                _persist(startData.thread_id, startData.user_id);
                setThreadId(startData.thread_id);
                setUserId(startData.user_id);
                if (startData.message) addMessage('assistant', startData.message);
                setStatus(startData.status);
                return;
            }

            _persist(customThreadId, data.user_id || '');
            setThreadId(customThreadId);
            setUserId(data.user_id);

            const restored = (data.messages || []).map((m, i) => {
                const role = m.role || (m.type === 'ai' ? 'assistant' : m.type === 'human' ? 'user' : m.type);
                // Gemini can return content as a list of blocks: [{type:'text', text:'...'}]
                // Normalize to a plain string so React components don't choke.
                const rawContent = m.content;
                const content = Array.isArray(rawContent)
                    ? rawContent.map(b => (typeof b === 'string' ? b : (b?.text ?? ''))).join('')
                    : (rawContent ?? '');
                return {
                    id: `restored-${i}`,
                    role: role,
                    content: String(content),
                };
            });

            // Attach tool_calls from state to the most recent assistant message, if any
            if (data.tool_calls && data.tool_calls.length > 0) {
                for (let i = restored.length - 1; i >= 0; i--) {
                    if (restored[i].role === 'assistant') {
                        restored[i].toolCalls = data.tool_calls;
                        break;
                    }
                }
            }

            // If the session has a pending question but it isn't in the message
            // log yet (e.g. first question before any answer), append it so it
            // always appears in the UI.
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

        try {
            const data = await resumeSession(threadId, text);
            if (data.message) {
                const rawMsg = data.message;
                const msgStr = typeof rawMsg === 'string'
                    ? rawMsg
                    : Array.isArray(rawMsg)
                        ? rawMsg.map(b => (typeof b === 'string' ? b : (b?.text ?? ''))).join('')
                        : typeof rawMsg === 'object' && rawMsg !== null
                            ? (rawMsg.text || JSON.stringify(rawMsg))
                            : String(rawMsg ?? '');

                setMessages(prev => [...prev, {
                    id: `${Date.now()}-${Math.random()}`,
                    role: 'assistant',
                    content: msgStr,
                    toolCalls: data.tool_calls || [],
                }]);
            }
            setStatus(data.status);
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
    }, []);

    return {
        messages,
        threadId,
        userId,
        profile,
        status,
        error,
        isLoading: status === 'loading',
        isComplete: status === 'complete',
        isInterrupted: status === 'interrupted',
        startSession,
        loadSession,
        sendAnswer,
        resetSession,
    };
}
