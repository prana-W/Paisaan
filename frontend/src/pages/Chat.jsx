import { useEffect, useRef, useState } from 'react';
import { useSession } from '@/hooks/useSession';
import { Send, RotateCcw, TrendingUp, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';

/* ── Typing indicator ──────────────────────────────────────────────────────── */
function TypingIndicator() {
    return (
        <div className="flex items-end gap-3 animate-bubble-in">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                <TrendingUp size={14} className="text-primary" />
            </div>
            <div className="glass px-4 py-3 rounded-2xl rounded-bl-sm flex gap-1.5 items-center">
                {[0, 150, 300].map(delay => (
                    <span
                        key={delay}
                        className="w-2 h-2 rounded-full bg-primary/60"
                        style={{ animation: `typingDot 1.2s ${delay}ms infinite` }}
                    />
                ))}
            </div>
        </div>
    );
}

/* ── Chat bubble ───────────────────────────────────────────────────────────── */
function ChatBubble({ message }) {
    const isAssistant = message.role === 'assistant';

    return (
        <div
            className={`flex items-end gap-3 animate-bubble-in ${
                isAssistant ? '' : 'flex-row-reverse'
            }`}
        >
            {/* Avatar */}
            {isAssistant ? (
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                    <TrendingUp size={14} className="text-primary" />
                </div>
            ) : (
                <div className="w-8 h-8 rounded-full bg-surface-2 border border-border flex items-center justify-center flex-shrink-0 text-xs font-semibold text-muted-foreground">
                    You
                </div>
            )}

            {/* Bubble */}
            <div
                className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                    isAssistant
                        ? 'glass rounded-bl-sm text-foreground'
                        : 'bg-primary text-primary-foreground rounded-br-sm'
                }`}
            >
                {message.content}
            </div>
        </div>
    );
}

/* ── Chat page ─────────────────────────────────────────────────────────────── */
export default function Chat() {
    const {
        messages, status, error, isLoading, isComplete,
        startSession, sendAnswer, resetSession,
    } = useSession();

    const [input, setInput] = useState('');
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    // Auto-start session on mount if idle
    useEffect(() => {
        if (status === 'idle') {
            startSession();
        }
    }, []); // eslint-disable-line

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!input.trim() || isLoading || isComplete) return;
        sendAnswer(input.trim());
        setInput('');
        inputRef.current?.focus();
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            handleSubmit(e);
        }
    };

    return (
        <div className="flex flex-col h-full min-h-0">

            {/* ── Top bar ── */}
            <div className="glass border-b border-border px-6 py-3 flex items-center justify-between flex-shrink-0">
                <div className="flex items-center gap-3">
                    <div className="relative">
                        <div className="w-2.5 h-2.5 rounded-full bg-gain animate-pulse" />
                        <div className="absolute inset-0 w-2.5 h-2.5 rounded-full bg-gain/40 animate-ping" />
                    </div>
                    <span className="text-sm font-medium text-muted-foreground">
                        Investment Planning Session
                    </span>
                </div>
                <button
                    id="reset-session-btn"
                    onClick={resetSession}
                    title="Start over"
                    className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded-lg hover:bg-muted"
                >
                    <RotateCcw size={13} />
                    New session
                </button>
            </div>

            {/* ── Message thread ── */}
            <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 min-h-0">
                {messages.length === 0 && isLoading && (
                    <div className="flex justify-center items-center h-32">
                        <Loader2 size={24} className="text-primary animate-spin" />
                    </div>
                )}

                {messages.map(msg => (
                    <ChatBubble key={msg.id} message={msg} />
                ))}

                {isLoading && messages.length > 0 && <TypingIndicator />}

                {/* Error banner */}
                {error && (
                    <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-destructive/10 text-destructive text-sm animate-bubble-in">
                        <AlertCircle size={15} className="flex-shrink-0" />
                        {error}
                    </div>
                )}

                {/* Completion banner */}
                {isComplete && (
                    <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-gain/10 text-gain text-sm animate-bubble-in">
                        <CheckCircle2 size={15} className="flex-shrink-0" />
                        Session complete — check your portfolio for the results.
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* ── Input bar ── */}
            <div className="glass border-t border-border p-4 flex-shrink-0">
                <form
                    id="chat-form"
                    onSubmit={handleSubmit}
                    className="flex items-end gap-3"
                >
                    <textarea
                        id="chat-input"
                        ref={inputRef}
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={
                            isComplete
                                ? 'Session complete. Start a new session to plan again.'
                                : 'Type your answer and press Enter…'
                        }
                        disabled={isLoading || isComplete}
                        rows={1}
                        className="flex-1 resize-none bg-surface-2 border border-border rounded-xl px-4 py-3 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        style={{ minHeight: '44px', maxHeight: '120px' }}
                    />
                    <button
                        id="send-btn"
                        type="submit"
                        disabled={!input.trim() || isLoading || isComplete}
                        className="w-11 h-11 rounded-xl bg-primary text-primary-foreground flex items-center justify-center hover:opacity-90 active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
                    >
                        {isLoading
                            ? <Loader2 size={16} className="animate-spin" />
                            : <Send size={16} />
                        }
                    </button>
                </form>
                <p className="text-xs text-muted-foreground mt-2 text-center">
                    Simulation only — no real money is invested.
                </p>
            </div>
        </div>
    );
}
