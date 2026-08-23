import { useEffect, useRef, useState } from 'react';
import { useSession } from '@/hooks/useSession';
import { getSessions } from '@/utils/api';
import {
    Send, RotateCcw, TrendingUp, Loader2, AlertCircle,
    CheckCircle2, ArrowRight, MessageSquare, Plus, Menu, X, Bot, User
} from 'lucide-react';

function TypingIndicator() {
    return (
        <div className="flex items-start gap-4 animate-bubble-in">
            <div className="w-8 h-8 rounded-lg bg-[var(--primary)]/10 flex items-center justify-center flex-shrink-0 border border-[var(--primary)]/20">
                <Bot size={16} style={{ color: 'var(--primary)' }} />
            </div>
            <div className="flex-1 space-y-1">
                <div className="text-xs font-semibold text-[var(--foreground)] opacity-90">Paisaan</div>
                <div className="glass px-4 py-3 rounded-2xl rounded-tl-sm flex gap-1.5 items-center w-max">
                    {[0, 150, 300].map(delay => (
                        <span
                            key={delay}
                            className="w-1.5 h-1.5 rounded-full"
                            style={{
                                background: 'var(--primary)',
                                opacity: 0.6,
                                animation: `typingDot 1.2s ${delay}ms infinite`,
                            }}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}

function ChatBubble({ message }) {
    const isAssistant = message.role === 'assistant';
    return (
        <div className={`flex items-start gap-4 animate-bubble-in ${isAssistant ? '' : 'flex-row-reverse'}`}>
            {isAssistant ? (
                <div className="w-8 h-8 rounded-lg bg-[var(--primary)]/10 flex items-center justify-center flex-shrink-0 border border-[var(--primary)]/20">
                    <Bot size={16} style={{ color: 'var(--primary)' }} />
                </div>
            ) : (
                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-semibold bg-[var(--surface-2)] text-[var(--muted-foreground)] border border-[var(--border)]">
                    <User size={14} />
                </div>
            )}
            <div className={`flex-1 space-y-1.5 ${isAssistant ? '' : 'text-right'}`}>
                <div className="text-xs font-semibold text-[var(--muted-foreground)]">
                    {isAssistant ? 'Paisaan' : 'You'}
                </div>
                <div
                    className={`inline-block text-left text-sm leading-relaxed px-4 py-3 rounded-2xl max-w-[85%]`}
                    style={isAssistant
                        ? { background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--foreground)' }
                        : { background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--foreground)' }
                    }
                >
                    {message.content}
                </div>
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
        <div className="flex-1 flex items-center justify-center p-6 bg-[var(--background)]">
            <div className="w-full max-w-lg space-y-8">
                <div className="text-center space-y-3">
                    <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto shadow-md"
                        style={{ background: 'var(--primary)' }}>
                        <Bot size={28} style={{ color: 'var(--primary-foreground)' }} />
                    </div>
                    <h1 className="text-3xl font-bold gradient-text">Namaste, I'm Paisaan</h1>
                    <p className="text-sm max-w-sm mx-auto" style={{ color: 'var(--muted-foreground)' }}>
                        Your AI-powered personal investment advisor. Let's design a custom portfolio tailored to your goals.
                    </p>
                </div>

                <form id="landing-form" onSubmit={handleSubmit} className="glass rounded-2xl p-6 space-y-5 shadow-sm">
                    <div className="space-y-2">
                        <label htmlFor="session-id-input" className="text-sm font-medium" style={{ color: 'var(--foreground)' }}>
                            Choose a Session ID <span style={{ color: 'var(--muted-foreground)' }}>(optional)</span>
                        </label>
                        <input
                            id="session-id-input"
                            type="text"
                            value={inputId}
                            onChange={e => { setInputId(e.target.value); setIdError(''); }}
                            placeholder="e.g. my-retirement-plan"
                            className="w-full rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)] transition-all"
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
                            Entering an existing ID restores your conversation, while a blank/new ID starts a fresh session.
                        </p>
                    </div>

                    <button
                        id="start-session-btn"
                        type="submit"
                        className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold transition-all hover:opacity-95 active:scale-[0.98]"
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
    const [sessionsList, setSessionsList] = useState([]);
    const [sidebarOpen, setSidebarOpen] = useState(false);

    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    const fetchSessions = async () => {
        try {
            const list = await getSessions();
            setSessionsList(list);
        } catch (err) {
            console.error('Failed to fetch sessions:', err);
        }
    };

    useEffect(() => {
        fetchSessions();
    }, [threadId]);

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
        setSidebarOpen(false);
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!input.trim() || isLoading || isComplete) return;
        sendAnswer(input.trim());
        setInput('');
        inputRef.current?.focus();
    };

    const handleNewChat = () => {
        resetSession();
        setSidebarOpen(false);
    };

    const handleSelectSession = (tid) => {
        loadSession(tid);
        setSidebarOpen(false);
    };

    return (
        <div className="flex h-full w-full overflow-hidden bg-[var(--background)] relative">
            {/* Mobile Sidebar Overlay Backdrop */}
            {sidebarOpen && (
                <div 
                    className="absolute inset-0 bg-black/50 z-30 lg:hidden transition-opacity" 
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Left Sidebar */}
            <div className={`
                absolute inset-y-0 left-0 z-40 w-64 bg-[var(--card)] border-r border-[var(--border)] flex flex-col transition-transform duration-300 ease-in-out lg:static lg:translate-x-0
                ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
            `}>
                {/* Sidebar Header */}
                <div className="h-14 border-b border-[var(--border)] px-4 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-[var(--primary)] flex items-center justify-center">
                            <TrendingUp size={16} style={{ color: 'var(--primary-foreground)' }} />
                        </div>
                        <span className="font-bold text-sm text-[var(--foreground)] tracking-wide">PAISAAN</span>
                    </div>
                    {/* Mobile Close Button */}
                    <button 
                        className="lg:hidden p-1.5 rounded-lg hover:bg-[var(--surface-2)] text-[var(--muted-foreground)]"
                        onClick={() => setSidebarOpen(false)}
                    >
                        <X size={16} />
                    </button>
                </div>

                {/* Sidebar Action Button */}
                <div className="p-3.5">
                    <button
                        onClick={handleNewChat}
                        className="flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-xl border border-[var(--border)] text-sm font-medium transition-all hover:bg-[var(--surface-2)] active:scale-[0.98]"
                        style={{ color: 'var(--foreground)' }}
                    >
                        <Plus size={16} />
                        New Chat
                    </button>
                </div>

                {/* Scrollable Conversation List */}
                <div className="flex-1 overflow-y-auto px-2 space-y-4 pb-4">
                    <div className="space-y-1">
                        <div className="px-3 text-[10px] font-bold text-[var(--muted-foreground)] uppercase tracking-wider mb-2">
                            Conversations
                        </div>
                        {sessionsList.length === 0 ? (
                            <div className="px-3 py-2 text-xs text-[var(--muted-foreground)] italic">
                                No recent conversations
                            </div>
                        ) : (
                            sessionsList.map(session => {
                                const isActive = threadId === session.thread_id;
                                return (
                                    <button
                                        key={session.thread_id}
                                        onClick={() => handleSelectSession(session.thread_id)}
                                        className={`
                                            flex items-center gap-2.5 w-full px-3 py-2.5 rounded-xl text-xs font-medium text-left truncate transition-colors border
                                            ${isActive 
                                                ? 'bg-[var(--primary)]/10 text-[var(--primary)] border-[var(--primary)]/20' 
                                                : 'bg-transparent border-transparent hover:bg-[var(--surface-2)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]'
                                            }
                                        `}
                                    >
                                        <MessageSquare size={13} className="flex-shrink-0" />
                                        <span className="truncate flex-1">{session.thread_id}</span>
                                    </button>
                                );
                            })
                        )}
                    </div>
                </div>
            </div>

            {/* Right Main Container */}
            <div className="flex-1 flex flex-col h-full min-h-0 overflow-hidden bg-[var(--background)]">
                {/* Header Bar */}
                <div className="h-14 border-b border-[var(--border)] px-4 flex items-center justify-between bg-[var(--card)] flex-shrink-0">
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => setSidebarOpen(true)}
                            className="lg:hidden p-1.5 rounded-lg hover:bg-[var(--surface-2)] text-[var(--muted-foreground)] flex-shrink-0"
                        >
                            <Menu size={18} />
                        </button>
                        {threadId && (
                            <div className="flex items-center gap-2.5">
                                <div className="relative flex-shrink-0">
                                    <div className="w-2 h-2 rounded-full" style={{ background: isComplete ? 'var(--gain)' : 'var(--primary)' }} />
                                    {!isComplete && (
                                        <div className="absolute inset-0 w-2 h-2 rounded-full animate-ping"
                                            style={{ background: 'var(--primary)', opacity: 0.4 }} />
                                    )}
                                </div>
                                <span className="text-xs font-medium text-[var(--muted-foreground)] truncate max-w-[200px] sm:max-w-none">
                                    Session: {threadId}
                                </span>
                            </div>
                        )}
                    </div>
                    {threadId && (
                        <button
                            onClick={handleNewChat}
                            className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--foreground)]"
                            style={{ color: 'var(--muted-foreground)' }}
                        >
                            <RotateCcw size={12} />
                            Reset Chat
                        </button>
                    )}
                </div>

                {/* Main Content Pane */}
                <div className="flex-1 overflow-hidden flex flex-col min-h-0">
                    {status === 'idle' || !threadId ? (
                        <Landing onStart={handleStart} />
                    ) : (
                        <>
                            {/* Message Log */}
                            <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6 min-h-0">
                                <div className="max-w-3xl mx-auto space-y-6 w-full">
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
                            </div>

                            {/* Claude-style Bottom Input Area */}
                            <div className="px-4 pb-6 pt-2 bg-gradient-to-t from-[var(--background)] to-transparent flex-shrink-0">
                                <div className="max-w-3xl mx-auto w-full">
                                    <form id="chat-form" onSubmit={handleSubmit} className="relative flex flex-col border border-[var(--border)] rounded-2xl bg-[var(--card)] shadow-sm focus-within:ring-1 focus-within:ring-[var(--primary)] focus-within:border-[var(--primary)] transition-all p-2.5">
                                        <textarea
                                            id="chat-input"
                                            ref={inputRef}
                                            value={input}
                                            onChange={e => setInput(e.target.value)}
                                            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e); } }}
                                            placeholder={isComplete ? 'Profile complete.' : 'Type your message...'}
                                            disabled={isLoading || isComplete}
                                            rows={1}
                                            className="w-full resize-none bg-transparent border-0 p-1.5 text-sm focus:outline-none focus:ring-0 placeholder-[var(--muted-foreground)] pr-12 min-h-[44px] max-h-[160px] text-[var(--foreground)]"
                                        />
                                        <div className="flex items-center justify-between mt-1 pt-1.5 border-t border-[var(--border)]/10">
                                            <span className="text-[10px] text-[var(--muted-foreground)] pl-1.5 hidden sm:inline">
                                                Press Enter to send, Shift+Enter for new line
                                            </span>
                                            <div className="flex-1 sm:flex-initial" />
                                            <button
                                                id="send-btn"
                                                type="submit"
                                                disabled={!input.trim() || isLoading || isComplete}
                                                className="w-8 h-8 rounded-lg flex items-center justify-center transition-all flex-shrink-0 ml-auto"
                                                style={{ 
                                                    background: input.trim() && !isLoading && !isComplete ? 'var(--primary)' : 'var(--surface-2)', 
                                                    color: input.trim() && !isLoading && !isComplete ? 'var(--primary-foreground)' : 'var(--muted-foreground)' 
                                                }}
                                            >
                                                {isLoading ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                                            </button>
                                        </div>
                                    </form>
                                    <p className="text-[10px] mt-2 text-center text-[var(--muted-foreground)]">
                                        Simulation only — no real money is invested.
                                    </p>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
