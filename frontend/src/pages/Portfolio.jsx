import { useState, useEffect } from 'react';
import { TrendingUp, BarChart2, Clock, Briefcase, Activity, Plus, X } from 'lucide-react';
import { getPortfolio } from '@/utils/api';
import { useRazorpay } from '@/hooks/useRazorpay';

function StatCard({ label, value, subtext, colorVar = 'var(--foreground)' }) {
    return (
        <div className="glass rounded-2xl p-5 space-y-1">
            <p className="text-xs uppercase tracking-wider" style={{ color: 'var(--muted-foreground)' }}>{label}</p>
            <p className="text-2xl font-bold font-mono" style={{ color: colorVar }}>{value}</p>
            {subtext && <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>{subtext}</p>}
        </div>
    );
}

export default function Portfolio() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showFundModal, setShowFundModal] = useState(false);
    const [fundAmount, setFundAmount] = useState('10000');
    const [notification, setNotification] = useState(null);

    const userId = sessionStorage.getItem('paisaan_user_id');
    const { processPayment, isProcessing } = useRazorpay(userId, null);

    const showNotif = (message, type = 'success') => {
        setNotification({ message, type });
        setTimeout(() => setNotification(null), 3000);
    };

    async function fetchPortfolio() {
        try {
            if (!userId) {
                setLoading(false);
                return;
            }
            const result = await getPortfolio(userId);
            setData(result);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        fetchPortfolio();
    }, [userId]);

    const handleFundWallet = async () => {
        const amt = parseFloat(fundAmount);
        if (isNaN(amt) || amt <= 0) {
            showNotif("Please enter a valid amount", "error");
            return;
        }
        try {
            await processPayment(amt);
            showNotif('Wallet funded successfully!', 'success');
            setShowFundModal(false);
            fetchPortfolio();
        } catch(err) {
            if (err.message) showNotif(err.message, 'error');
        }
    };

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="animate-pulse space-y-4 flex flex-col items-center">
                    <div className="w-10 h-10 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
                    <p className="text-sm text-[var(--muted-foreground)]">Loading portfolio...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <p className="text-red-500 bg-red-500/10 px-4 py-2 rounded-xl text-sm">{error}</p>
            </div>
        );
    }

    const hasHoldings = data && data.holdings && data.holdings.length > 0;

    return (
        <div className="flex-1 overflow-y-auto px-6 py-8 relative">
            {notification && (
                <div className="fixed top-4 right-4 z-50 animate-bubble-in bg-[var(--card)] border border-[var(--border)] shadow-lg rounded-xl px-4 py-3 flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${notification.type === 'error' ? 'bg-red-500' : 'bg-green-500'}`} />
                    <p className="text-sm font-medium">{notification.message}</p>
                </div>
            )}

            <div className="max-w-4xl mx-auto w-full space-y-8 pb-12">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold gradient-text">Your Portfolio</h1>
                        <p className="text-sm mt-1" style={{ color: 'var(--muted-foreground)' }}>
                            Simulation only — tracks how Paisaan's recommendations would have performed.
                        </p>
                    </div>
                    <button 
                        onClick={() => setShowFundModal(true)}
                        className="flex items-center gap-2 bg-[var(--primary)] text-[var(--primary-foreground)] px-4 py-2 rounded-xl text-sm font-semibold hover:opacity-95 transition-all"
                    >
                        <Plus size={16} />
                        Add Money
                    </button>
                </div>

                {showFundModal && (
                    <div className="glass rounded-2xl p-6 border border-[var(--primary)]/20 shadow-lg animate-bubble-in relative max-w-sm">
                        <button 
                            onClick={() => setShowFundModal(false)}
                            className="absolute top-4 right-4 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                        >
                            <X size={16} />
                        </button>
                        <h3 className="text-lg font-bold mb-1">Fund Wallet</h3>
                        <p className="text-xs text-[var(--muted-foreground)] mb-4">Add mock funds to your Paisaan virtual wallet.</p>
                        
                        <div className="flex items-center gap-2 text-2xl font-bold border-b border-[var(--border)] focus-within:border-[var(--primary)] pb-2 mb-6">
                            <span>₹</span>
                            <input 
                                type="number" 
                                value={fundAmount}
                                onChange={(e) => setFundAmount(e.target.value)}
                                className="bg-transparent outline-none flex-1 w-full"
                                autoFocus
                            />
                        </div>
                        <button 
                            onClick={handleFundWallet}
                            disabled={isProcessing}
                            className="w-full bg-[#3399cc] text-white py-2.5 rounded-xl text-sm font-semibold hover:opacity-95 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
                        >
                            {isProcessing ? 'Processing...' : 'Pay via Razorpay'}
                        </button>
                    </div>
                )}

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <StatCard 
                        label="Wallet Balance" 
                        value={`₹${data?.wallet_balance?.toLocaleString('en-IN') || 0}`} 
                        subtext="Available funds" 
                        colorVar="var(--primary)"
                    />
                    <StatCard 
                        label="Invested" 
                        value={`₹${data?.total_invested?.toLocaleString('en-IN') || 0}`} 
                        subtext={hasHoldings ? `${data.holdings.length} holdings` : "No holdings yet"} 
                    />
                    <StatCard 
                        label="Current Value" 
                        value={`₹${data?.current_value?.toLocaleString('en-IN') || 0}`} 
                        subtext="Simulated" 
                    />
                    <StatCard 
                        label="Gain / Loss" 
                        value={`${data?.gain_loss >= 0 ? '+' : ''}₹${data?.gain_loss?.toLocaleString('en-IN') || 0}`} 
                        subtext={`${data?.gain_loss_pct > 0 ? '+' : ''}${data?.gain_loss_pct || 0}% Return`} 
                        colorVar={data?.gain_loss > 0 ? 'var(--gain)' : data?.gain_loss < 0 ? 'var(--destructive)' : 'var(--muted-foreground)'} 
                    />
                </div>

                {!hasHoldings ? (
                    <div className="glass rounded-2xl p-12 flex flex-col items-center justify-center gap-4 text-center mt-8">
                        <div className="w-16 h-16 rounded-2xl flex items-center justify-center" style={{ background: 'var(--primary)/10' }}>
                            <BarChart2 size={28} style={{ color: 'var(--primary)' }} />
                        </div>
                        <div>
                            <h2 className="font-semibold" style={{ color: 'var(--foreground)' }}>No holdings yet</h2>
                            <p className="text-sm mt-1 max-w-xs" style={{ color: 'var(--muted-foreground)' }}>
                                Complete a planning session in the Chat tab and fund your wallet to get your first investment allocation.
                            </p>
                        </div>
                    </div>
                ) : (
                    <>
                        {/* Holdings Allocation */}
                        <div className="glass rounded-2xl p-6 space-y-6">
                            <div className="flex items-center gap-2 text-sm font-medium" style={{ color: 'var(--foreground)' }}>
                                <Briefcase size={16} style={{ color: 'var(--primary)' }} />
                                Current Allocations
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {data.holdings.map((h, i) => (
                                    <div key={i} className="flex justify-between items-center p-4 rounded-xl border border-[var(--border)] bg-[var(--surface-2)]/30 hover:bg-[var(--surface-2)]/50 transition-colors">
                                        <div className="flex flex-col">
                                            <span className="font-semibold text-sm">{h.source}</span>
                                            <span className="text-xs text-[var(--muted-foreground)]">{h.percent_allocation}% of plan</span>
                                        </div>
                                        <div className="text-right">
                                            <div className="font-mono font-medium text-sm">₹{h.invested.toLocaleString('en-IN')}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Transaction History */}
                        <div className="glass rounded-2xl p-6 space-y-6">
                            <div className="flex items-center gap-2 text-sm font-medium" style={{ color: 'var(--foreground)' }}>
                                <Activity size={16} style={{ color: 'var(--primary)' }} />
                                Transaction History
                            </div>
                            <div className="space-y-3">
                                {data.transactions.map((txn, i) => (
                                    <div key={txn.id || i} className="flex items-center justify-between py-3 px-1 border-b border-[var(--border)]/50 last:border-0">
                                        <div className="flex flex-col gap-0.5">
                                            <span className="text-sm font-medium capitalize flex items-center gap-2">
                                                <span className={`w-1.5 h-1.5 rounded-full ${txn.action === 'buy' ? 'bg-green-500' : 'bg-blue-500'}`} />
                                                {txn.action} {txn.source}
                                            </span>
                                            <span className="text-xs text-[var(--muted-foreground)] font-mono">
                                                {new Date(txn.date).toLocaleString()}
                                            </span>
                                        </div>
                                        <span className="text-sm font-mono font-bold" style={{ color: txn.action === 'buy' ? 'var(--foreground)' : 'var(--gain)' }}>
                                            {txn.action === 'buy' ? '-' : '+'}₹{txn.amount.toLocaleString('en-IN')}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
