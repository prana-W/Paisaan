import { useEffect, useRef, useState } from 'react';
import { useSession } from '@/hooks/useSession';
import { Send, RotateCcw, TrendingUp, Loader2, AlertCircle, CheckCircle2, ArrowRight } from 'lucide-react';

function TypingIndicator() {
    return (
        <div className="flex items-end gap-3 animate-bubble-in">
            <div className="w-8 h-8 rounded-full bg-[var(--primary)]/20 flex items-center justify-center flex-shrink-0">
                <TrendingUp size={14} style={{ color: 'var(--primary)' }} />
            </div>
            <div className="glass px-4 py-3 rounded-2xl rounded-bl-sm flex gap-1.5 items-center">
                {[0, 150, 300].map(delay => (
                    <span
                        key={delay}
                        className="w-2 h-2 rounded-full"
                        style={{
                            background: 'var(--primary)',
                            opacity: 0.6,
                            animation: `typingDot 1.2s ${delay}ms infinite`,
                        }}
                    />
                ))}
            </div>
        </div>
    );
}

function ChatBubble({ message }) {
    const isAssistant = message.role === 'assistant';
    return (
        <div className={`flex items-end gap-3 animate-bubble-in ${isAssistant ? '' : 'flex-row-reverse'}`}>
            {isAssistant ? (
                <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ background: 'var(--primary)/20' }}>
                    <TrendingUp size={14} style={{ color: 'var(--primary)' }} />
                </div>
            ) : (
                <div className="w-8 h-8 rounded-full border flex items-center justify-center flex-shrink-0 text-xs font-semibold"
                    style={{ borderColor: 'var(--border)', color: 'var(--muted-foreground)', background: 'var(--surface-2)' }}>
                    You
                </div>
            )}
            <div
                className="max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed"
                style={isAssistant
                    ? { background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--foreground)' }
                    : { background: 'var(--primary)', color: 'var(--primary-foreground)' }
                }
            >
                {message.content}
            </div>
        </div>
    );
}

function Landing({ onStart }) {
    const [inputId, setInputId] = useState('');
    const [idError, setIdError] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        const trimmed = inputId.trim();
        if (trimmed && /\s/.test(trimmed)) {
            setIdError('Session ID cannot contain spaces');
            return;
        }
        setIdError('');
        onStart(trimmed || null);
    };

    return (
        <div className="flex-1 flex items-center justify-center p-6">
            <div className="w-full max-w-md space-y-8">
                <div className="text-center space-y-2">
                    <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto shadow-lg"
                        style={{ background: 'var(--primary)' }}>
                        <TrendingUp size={28} style={{ color: 'var(--primary-foreground)' }} />
                    </div>
                    <h1 className="text-2xl font-bold gradient-text">Paisaan</h1>
                    <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>
                        Your personal AI investment advisor
                    </p>
                </div>

                <form id="landing-form" onSubmit={handleSubmit} className="glass rounded-2xl p-6 space-y-5">
                    <div className="space-y-1.5">
                        <label htmlFor="session-id-input" className="text-sm font-medium" style={{ color: 'var(--foreground)' }}>
                            Session ID <span style={{ color: 'var(--muted-foreground)' }}>(optional)</span>
                        </label>
                        <input
                            id="session-id-input"
                            type="text"
                            value={inputId}
                            onChange={e => { setInputId(e.target.value); setIdError(''); }}
                            placeholder="e.g. my-portfolio or leave blank"
                            className="w-full rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 transition-all"
                            style={{
                                background: 'var(--surface-2)',
                                border: `1px solid ${idError ? 'var(--destructive)' : 'var(--border)'}`,
                                color: 'var(--foreground)',
                            }}
                        />
                        {idError && (
                            <p className="text-xs" style={{ color: 'var(--destructive)' }}>{idError}</p>
                        )}
                        <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
                            Enter an existing ID to resume a past session, or a new one to track this session.
                        </p>
                    </div>

                    <button
                        id="start-session-btn"
                        type="submit"
                        className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all hover:opacity-90 active:scale-95"
                        style={{ background: 'var(--primary)', color: 'var(--primary-foreground)' }}
                    >
                        Begin Planning
                        <ArrowRight size={16} />
                    </button>
                </form>

                <p className="text-center text-xs" style={{ color: 'var(--muted-foreground)' }}>
                    Simulation only — no real money is invested.
                </p>
            </div>
        </div>
    );
}

export default function Chat() {
    const {
        messages, threadId, status, error, isLoading, isComplete,
        startSession, loadSession, sendAnswer, resetSession,
    } = useSession();

    const [input, setInput] = useState('');
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    useEffect(() => {
        const savedThreadId = sessionStorage.getItem('paisaan_thread_id');
        if (savedThreadId && status === 'idle') {
            loadSession(savedThreadId);
        }
    }, [loadSession, status]);

    const handleStart = (customId) => {
        if (customId) {
            loadSession(customId);
        } else {
            startSession();
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!input.trim() || isLoading || isComplete) return;
        sendAnswer(input.trim());
        setInput('');
        inputRef.current?.focus();
    };

    if (status === 'idle') {
        return <Landing onStart={handleStart} />;
    }

    return (
        <div className="flex flex-col h-full min-h-0">
            <div className="border-b px-6 py-3 flex items-center justify-between flex-shrink-0"
                style={{ background: 'var(--card)', borderColor: 'var(--border)' }}>
                <div className="flex items-center gap-3">
                    <div className="relative">
                        <div className="w-2.5 h-2.5 rounded-full" style={{ background: 'var(--gain)' }} />
                        <div className="absolute inset-0 w-2.5 h-2.5 rounded-full animate-ping"
                            style={{ background: 'var(--gain)', opacity: 0.4 }} />
                    </div>
                    <span className="text-sm font-medium" style={{ color: 'var(--muted-foreground)' }}>
                        {threadId ? `Session: ${threadId}` : 'Investment Planning Session'}
                    </span>
                </div>
                <button
                    id="reset-session-btn"
                    onClick={resetSession}
                    className="flex items-center gap-1.5 text-xs px-2 py-1 rounded-lg transition-colors hover:opacity-80"
                    style={{ color: 'var(--muted-foreground)' }}
                >
                    <RotateCcw size={13} />
                    New session
                </button>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 min-h-0">
                {messages.length === 0 && isLoading && (
                    <div className="flex justify-center items-center h-32">
                        <Loader2 size={24} className="animate-spin" style={{ color: 'var(--primary)' }} />
                    </div>
                )}

                {messages.map(msg => <ChatBubble key={msg.id} message={msg} />)}

                {isLoading && messages.length > 0 && <TypingIndicator />}

                {error && (
                    <div className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm animate-bubble-in"
                        style={{ background: 'var(--destructive)/10', color: 'var(--destructive)' }}>
                        <AlertCircle size={15} className="flex-shrink-0" />
                        {error}
                    </div>
                )}

                {isComplete && (
                    <div className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm animate-bubble-in"
                        style={{ background: 'var(--gain)/10', color: 'var(--gain)' }}>
                        <CheckCircle2 size={15} className="flex-shrink-0" />
                        Profile complete — your investment plan is being prepared.
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            <div className="border-t p-4 flex-shrink-0"
                style={{ background: 'var(--card)', borderColor: 'var(--border)' }}>
                <form id="chat-form" onSubmit={handleSubmit} className="flex items-end gap-3">
                    <textarea
                        id="chat-input"
                        ref={inputRef}
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) handleSubmit(e); }}
                        placeholder={isComplete ? 'Profile complete.' : 'Type your answer and press Enter…'}
                        disabled={isLoading || isComplete}
                        rows={1}
                        className="flex-1 resize-none rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        style={{
                            background: 'var(--surface-2)',
                            border: '1px solid var(--border)',
                            color: 'var(--foreground)',
                            minHeight: '44px',
                            maxHeight: '120px',
                        }}
                    />
                    <button
                        id="send-btn"
                        type="submit"
                        disabled={!input.trim() || isLoading || isComplete}
                        className="w-11 h-11 rounded-xl flex items-center justify-center transition-all hover:opacity-90 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
                        style={{ background: 'var(--primary)', color: 'var(--primary-foreground)' }}
                    >
                        {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                    </button>
                </form>
                <p className="text-xs mt-2 text-center" style={{ color: 'var(--muted-foreground)' }}>
                    Simulation only — no real money is invested.
                </p>
            </div>
        </div>
    );
}
