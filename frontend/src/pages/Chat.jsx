import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useSession } from '@/hooks/useSession';
import { getSessions, deleteSession } from '@/utils/api';
import {
    Send, RotateCcw, TrendingUp, Loader2, AlertCircle,
    CheckCircle2, ArrowRight, MessageSquare, Plus, Menu, X, Bot, User, Trash2, ChevronDown, ChevronRight, CheckCircle, Wrench
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

const PREVIEW_LIMIT = 160;

function ToolCallRow({ tc }) {
    const [expanded, setExpanded] = useState(false);
    const full = tc.result_preview || '';
    const isLong = full.length > PREVIEW_LIMIT;
    const preview = isLong ? full.slice(0, PREVIEW_LIMIT) + '…' : full;

    return (
        <div className="flex flex-col gap-1 px-3 py-2.5 rounded-xl border border-[var(--border)]/50 bg-[var(--background)] ml-3">
            {/* Tool name row */}
            <div className="flex items-center gap-2">
                {tc.status === 'success' ? (
                    <CheckCircle size={12} className="text-gain flex-shrink-0" />
                ) : (
                    <AlertCircle size={12} className="text-destructive flex-shrink-0" />
                )}
                <span className="text-xs font-medium text-[var(--foreground)] flex-1">{tc.name}</span>
            </div>

            {/* Result */}
            {full && (
                <div className="pl-5">
                    {expanded ? (
                        <pre
                            className="text-[10px] text-[var(--muted-foreground)] font-mono whitespace-pre-wrap break-all max-h-64 overflow-y-auto rounded-lg p-2"
                            style={{ background: 'var(--surface-2)' }}
                        >
                            {full}
                        </pre>
                    ) : (
                        <span className="text-[10px] text-[var(--muted-foreground)] font-mono opacity-70 break-all">
                            {preview}
                        </span>
                    )}
                    {isLong && (
                        <button
                            onClick={() => setExpanded(e => !e)}
                            className="mt-1 text-[10px] font-semibold transition-colors"
                            style={{ color: 'var(--primary)' }}
                        >
                            {expanded ? '▲ Collapse' : '▼ Show full result'}
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}

function ChatBubble({ message }) {
    const isAssistant = message.role === 'assistant';
    const hasTools = isAssistant && message.toolCalls && message.toolCalls.length > 0;
    const [toolsExpanded, setToolsExpanded] = useState(false);

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
                
                {/* Tool Calls Display */}
                {hasTools && (
                    <div className="mb-2 max-w-[85%]">
                        <button
                            onClick={() => setToolsExpanded(!toolsExpanded)}
                            className="flex items-center gap-2 px-3 py-2 w-full text-left rounded-xl border border-[var(--border)] bg-[var(--surface-2)]/50 hover:bg-[var(--surface-2)] transition-colors"
                        >
                            <div className="w-5 h-5 rounded-md bg-[var(--primary)]/10 flex items-center justify-center flex-shrink-0">
                                <Wrench size={12} className="text-[var(--primary)]" />
                            </div>
                            <span className="flex-1 text-xs font-semibold text-[var(--foreground)]">
                                Tools Called ({message.toolCalls.length})
                            </span>
                            {toolsExpanded ? <ChevronDown size={14} className="text-[var(--muted-foreground)]" /> : <ChevronRight size={14} className="text-[var(--muted-foreground)]" />}
                        </button>
                        
                        {toolsExpanded && (
                            <div className="mt-1.5 space-y-1.5">
                                {message.toolCalls.map((tc, idx) => (
                                    <ToolCallRow key={idx} tc={tc} />
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Main Message Content */}
                {message.content && (
                    <div
                        className={`inline-block text-left text-sm leading-relaxed px-4 py-3 rounded-2xl max-w-[85%]`}
                        style={isAssistant
                            ? { background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--foreground)' }
                            : { background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--foreground)' }
                        }
                    >
                        {isAssistant ? (
                            <div className="markdown-body">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {message.content}
                                </ReactMarkdown>
                            </div>
                        ) : (
                            message.content
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

function Landing({ onStart, error }) {
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

                    {error && (
                        <div className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm bg-red-500/10" style={{ color: 'var(--destructive)' }}>
                            <AlertCircle size={15} className="flex-shrink-0" />
                            <span>{error}</span>
                        </div>
                    )}

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
        messages, threadId, userId, profile, status, error, payload, isLoading, isComplete,
        startSession, loadSession, sendAnswer, resetSession,
    } = useSession();

    // Track when a session start/load has been initiated so we show
    // the chat pane immediately (before threadId is resolved)
    const [sessionStarted, setSessionStarted] = useState(() => {
        return !!sessionStorage.getItem('paisaan_thread_id');
    });

    const [input, setInput] = useState('');
    const [sessionsList, setSessionsList] = useState([]);
    const [sidebarOpen, setSidebarOpen] = useState(() => {
        const saved = localStorage.getItem('paisaan_sidebar_open');
        return saved !== null ? JSON.parse(saved) : window.innerWidth >= 1024;
    });
    const [confirmModal, setConfirmModal] = useState({ isOpen: false, title: '', message: '', onConfirm: null });
    const [notification, setNotification] = useState(null);

    const showNotification = (message, type = 'success') => {
        setNotification({ message, type });
        setTimeout(() => setNotification(null), 3000);
    };

    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);
    const [isProcessingPayment, setIsProcessingPayment] = useState(false);

    const fetchSessions = async () => {
        try {
            const list = await getSessions();
            setSessionsList(list);
        } catch (err) {
            console.error('Failed to fetch sessions:', err);
        }
    };

    useEffect(() => {
        localStorage.setItem('paisaan_sidebar_open', JSON.stringify(sidebarOpen));
    }, [sidebarOpen]);

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

    useEffect(() => {
        const handleToggle = () => setSidebarOpen(prev => !prev);
        window.addEventListener('toggle-sidebar', handleToggle);
        return () => window.removeEventListener('toggle-sidebar', handleToggle);
    }, []);

    const handleRazorpayPayment = async (paymentAmount = 10000) => { // Default to 10k mock funding
        if (!window.Razorpay) {
            showNotification('Razorpay SDK failed to load', 'error');
            return;
        }

        setIsProcessingPayment(true);
        try {
            // 1. Create order
            const orderRes = await fetch('http://localhost:9000/api/v1/wallet/create-order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, amount: paymentAmount })
            });
            const orderData = await orderRes.json();
            if (!orderRes.ok) throw new Error(orderData.detail || 'Failed to create order');

            // 2. Open Razorpay checkout
            const options = {
                key: "rzp_test_dummy_key", // Will be overridden by backend or just used for mock
                amount: orderData.amount * 100,
                currency: orderData.currency,
                name: "Paisaan Wallet",
                description: "Virtual Portfolio Funding",
                order_id: orderData.order_id,
                handler: async function (response) {
                    try {
                        // 3. Verify payment
                        const verifyRes = await fetch('http://localhost:9000/api/v1/wallet/verify-payment', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                razorpay_order_id: response.razorpay_order_id,
                                razorpay_payment_id: response.razorpay_payment_id,
                                razorpay_signature: response.razorpay_signature,
                                user_id: userId
                            })
                        });
                        const verifyData = await verifyRes.json();
                        if (!verifyRes.ok) throw new Error(verifyData.detail || 'Payment verification failed');

                        showNotification('Wallet funded successfully!', 'success');
                        // 4. Resume LangGraph with success
                        sendAnswer(response.razorpay_payment_id || 'success');
                    } catch (err) {
                        showNotification(err.message, 'error');
                        sendAnswer('failed');
                    }
                },
                prefill: {
                    name: profile?.name || "Test User",
                },
                theme: { color: "#3399cc" },
                modal: {
                    ondismiss: function() {
                        showNotification('Payment cancelled', 'error');
                        sendAnswer('failed');
                    }
                }
            };
            const rzp = new window.Razorpay(options);
            rzp.on('payment.failed', function (response) {
                showNotification(response.error.description, 'error');
                sendAnswer('failed');
            });
            rzp.open();
        } catch (err) {
            showNotification(err.message, 'error');
            sendAnswer('failed');
        } finally {
            setIsProcessingPayment(false);
        }
    };

    useEffect(() => {
        if (payload?.type === 'payment_required') {
            handleRazorpayPayment();
        }
    }, [payload]);

    const handleStart = (customId) => {
        setSessionStarted(true);
        if (customId) {
            loadSession(customId);
        } else {
            startSession();
        }
        if (window.innerWidth < 1024) {
            setSidebarOpen(false);
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!input.trim() || isLoading || isComplete) return;
        sendAnswer(input.trim());
        setInput('');
        inputRef.current?.focus();
    };

    const handleNewChat = () => {
        setSessionStarted(false);
        resetSession();
        if (window.innerWidth < 1024) {
            setSidebarOpen(false);
        }
    };

    const handleSelectSession = (tid) => {
        setSessionStarted(true);
        loadSession(tid);
        if (window.innerWidth < 1024) {
            setSidebarOpen(false);
        }
    };

    const handleDeleteSession = async (e, tid) => {
        e.stopPropagation();
        setConfirmModal({
            isOpen: true,
            title: 'Delete Conversation',
            message: `Are you sure you want to delete this conversation? This will permanently erase the thread history.`,
            onConfirm: async () => {
                const originalList = [...sessionsList];
                
                // Optimistic UI updates
                setSessionsList(prev => prev.filter(s => s.thread_id !== tid));
                let activeSessionDeleted = false;
                if (threadId === tid) {
                    activeSessionDeleted = true;
                    handleNewChat();
                }

                try {
                    await deleteSession(tid);
                    showNotification('Conversation deleted successfully', 'success');
                } catch (err) {
                    console.error('Failed to delete session:', err);
                    showNotification('Failed to delete conversation', 'error');
                    // Rollback on failure
                    setSessionsList(originalList);
                    if (activeSessionDeleted) {
                        loadSession(tid);
                    }
                }
            }
        });
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
                absolute inset-y-0 left-0 z-40 bg-[var(--card)] flex flex-col transition-all duration-300 ease-in-out lg:static
                ${sidebarOpen 
                    ? 'translate-x-0 w-64 border-r border-[var(--border)] opacity-100' 
                    : '-translate-x-full lg:translate-x-0 lg:w-0 lg:opacity-0 lg:pointer-events-none lg:border-r-0 overflow-hidden'
                }
            `}>
                {/* Sidebar Header */}
                <div className="h-14 border-b border-[var(--border)] px-4 flex items-center justify-between">
                    <span className="text-[10px] font-bold text-[var(--muted-foreground)] uppercase tracking-wider pl-1">
                        History
                    </span>
                    {/* Close Button */}
                    <button 
                        className="p-1.5 rounded-lg hover:bg-[var(--surface-2)] text-[var(--muted-foreground)]"
                        onClick={() => setSidebarOpen(false)}
                        title="Close Sidebar"
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
                                    <div
                                        key={session.thread_id}
                                        className={`
                                            group flex items-center justify-between w-full rounded-xl text-xs font-medium transition-colors border
                                            ${isActive 
                                                ? 'bg-[var(--primary)]/10 text-[var(--primary)] border-[var(--primary)]/20' 
                                                : 'bg-transparent border-transparent hover:bg-[var(--surface-2)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]'
                                            }
                                        `}
                                    >
                                        <button
                                            onClick={() => handleSelectSession(session.thread_id)}
                                            className="flex items-center gap-2.5 flex-1 px-3 py-2.5 text-left truncate min-w-0"
                                        >
                                            <MessageSquare size={13} className="flex-shrink-0" />
                                            <span className="truncate flex-1">{session.thread_id}</span>
                                        </button>
                                        <button
                                            onClick={(e) => handleDeleteSession(e, session.thread_id)}
                                            className="opacity-100 lg:opacity-0 lg:group-hover:opacity-100 p-1.5 mr-1.5 rounded-lg hover:bg-red-500/10 text-red-500/80 hover:text-red-500 transition-opacity"
                                            title="Delete Session"
                                        >
                                            <Trash2 size={13} />
                                        </button>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            </div>

            {/* Right Main Container */}
            <div className="flex-1 flex flex-col h-full min-h-0 overflow-hidden bg-[var(--background)]">
                {/* Main Content Pane */}
                <div className="flex-1 overflow-hidden flex flex-col min-h-0">
                    {!sessionStarted ? (
                        <Landing onStart={handleStart} error={error} />
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

                                    {payload?.type === 'payment_required' && !isProcessingPayment && (
                                        <div className="flex flex-col items-center gap-3 py-6 animate-bubble-in">
                                            <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-2xl text-center space-y-4 max-w-sm w-full">
                                                <div className="text-sm font-medium text-[var(--foreground)]">Complete Funding</div>
                                                <button 
                                                    onClick={() => handleRazorpayPayment()}
                                                    className="w-full py-2.5 rounded-xl text-sm font-semibold transition-all hover:opacity-95 active:scale-[0.98] bg-[#3399cc] text-white"
                                                >
                                                    Pay with Razorpay
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    {error && (
                                        <div className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm animate-bubble-in bg-destructive/10 text-destructive">
                                            <AlertCircle size={15} className="flex-shrink-0" />
                                            {error}
                                        </div>
                                    )}

                                    {isComplete && (
                                        <div className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm animate-bubble-in bg-gain/10 text-gain">
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

            {/* Custom Confirmation Modal */}
            {confirmModal.isOpen && (
                <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px] z-50 flex items-center justify-center p-4">
                    <div className="glass max-w-sm w-full p-6 rounded-2xl shadow-xl space-y-5 border border-[var(--border)] animate-bubble-in">
                        <div className="space-y-2">
                            <h3 className="font-bold text-sm text-[var(--foreground)]">{confirmModal.title}</h3>
                            <p className="text-xs text-[var(--muted-foreground)] leading-relaxed">{confirmModal.message}</p>
                        </div>
                        <div className="flex gap-2.5 justify-end">
                            <button
                                onClick={() => setConfirmModal({ ...confirmModal, isOpen: false })}
                                className="px-3.5 py-2 rounded-xl text-xs font-semibold hover:bg-[var(--surface-2)] transition-colors border border-[var(--border)] text-[var(--foreground)]"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => {
                                    confirmModal.onConfirm();
                                    setConfirmModal({ ...confirmModal, isOpen: false });
                                }}
                                className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-red-600 hover:bg-red-700 text-white transition-colors"
                            >
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Toast Notifications */}
            {notification && (
                <div className="absolute bottom-4 right-4 z-50 glass border border-[var(--border)] px-4 py-3 rounded-xl shadow-lg flex items-center gap-2.5 animate-bubble-in text-xs font-semibold">
                    {notification.type === 'error' ? (
                        <AlertCircle size={15} className="text-red-500 flex-shrink-0" />
                    ) : (
                        <CheckCircle2 size={15} className="text-emerald-500 flex-shrink-0" />
                    )}
                    <span className="text-[var(--foreground)]">{notification.message}</span>
                </div>
            )}
        </div>
    );
}
