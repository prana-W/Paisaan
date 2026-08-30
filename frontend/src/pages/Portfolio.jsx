import { useEffect, useState, useCallback, useRef } from 'react';
import {
    TrendingUp, TrendingDown, Wallet, Plus, X, Loader2,
    AlertCircle, CheckCircle2, BarChart2, RefreshCw, ArrowUpRight,
} from 'lucide-react';
import { getPortfolioSummary, getInvestments, getWalletBalance, createWalletOrder, verifyWalletPayment } from '@/utils/api';

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n, prefix = '₹') {
    if (n == null || isNaN(n)) return `${prefix}0`;
    return `${prefix}${Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtPct(n) {
    if (n == null || isNaN(n)) return '0.00%';
    return `${n >= 0 ? '+' : ''}${Number(n).toFixed(2)}%`;
}

function assetBadgeColor(type) {
    const map = {
        mutual_fund: 'oklch(0.65 0.15 185)',
        stock: 'oklch(0.70 0.16 85)',
        gold: 'oklch(0.80 0.16 85)',
        silver: 'oklch(0.62 0.02 70)',
        fd: 'oklch(0.65 0.16 45)',
        other: 'oklch(0.60 0.08 280)',
    };
    return map[type] || map.other;
}

function assetLabel(type) {
    const map = {
        mutual_fund: 'Mutual Fund',
        stock: 'Stock',
        gold: 'Gold',
        silver: 'Silver',
        fd: 'FD',
        other: 'Other',
    };
    return map[type] || type;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatCard({ label, value, subtext, color, icon: Icon, pulse }) {
    return (
        <div className={`glass rounded-2xl p-5 space-y-2 relative overflow-hidden transition-all hover:scale-[1.01] ${pulse ? 'ring-1 ring-[var(--primary)]/30' : ''}`}>
            {Icon && (
                <div className="absolute top-4 right-4 opacity-10">
                    <Icon size={32} />
                </div>
            )}
            <p className="text-xs uppercase tracking-wider font-medium" style={{ color: 'var(--muted-foreground)' }}>
                {label}
            </p>
            <p className="text-2xl font-bold font-mono" style={{ color: color || 'var(--foreground)' }}>
                {value}
            </p>
            {subtext && (
                <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
                    {subtext}
                </p>
            )}
        </div>
    );
}

function AddMoneyModal({ onClose, onSuccess }) {
    const [amount, setAmount] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const inputRef = useRef(null);

    useEffect(() => {
        inputRef.current?.focus();
        // Load Razorpay checkout script
        if (!window.Razorpay) {
            const script = document.createElement('script');
            script.src = 'https://checkout.razorpay.com/v1/checkout.js';
            document.body.appendChild(script);
        }
    }, []);

    const handlePay = async () => {
        const amt = parseFloat(amount);
        if (!amt || amt <= 0) {
            setError('Please enter a valid amount greater than ₹0');
            return;
        }
        setError('');
        setLoading(true);

        try {
            // 1. Create Razorpay order
            const order = await createWalletOrder(amt);

            // 2. Open Razorpay checkout
            const options = {
                key: order.razorpay_key_id,
                amount: order.amount_paise,
                currency: order.currency,
                name: 'Paisaan',
                description: 'Wallet Top-up',
                order_id: order.order_id,
                handler: async (response) => {
                    try {
                        // 3. Verify & credit wallet
                        const result = await verifyWalletPayment({
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_signature: response.razorpay_signature,
                            amount: amt,
                        });
                        if (result.success) {
                            onSuccess(result.new_balance);
                        } else {
                            setError('Payment verification failed. Please try again.');
                        }
                    } catch (err) {
                        setError('Payment verified but failed to credit wallet. Contact support.');
                    }
                    setLoading(false);
                },
                prefill: { name: 'Paisaan User', email: 'user@paisaan.app' },
                theme: { color: 'oklch(0.65 0.16 45)' },
                modal: {
                    ondismiss: () => setLoading(false),
                },
            };

            const rzp = new window.Razorpay(options);
            rzp.open();
        } catch (err) {
            setError(err?.data?.detail || 'Failed to create payment order. Please try again.');
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-[3px] z-50 flex items-center justify-center p-4">
            <div
                className="glass max-w-sm w-full p-6 rounded-2xl shadow-2xl space-y-5 border border-[var(--border)] animate-bubble-in"
                style={{ background: 'var(--card)' }}
            >
                {/* Header */}
                <div className="flex items-start justify-between">
                    <div className="space-y-1">
                        <h2 className="font-bold text-base" style={{ color: 'var(--foreground)' }}>
                            Add Money to Wallet
                        </h2>
                        <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
                            Powered by Razorpay (Test Mode)
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-lg hover:bg-[var(--surface-2)] transition-colors"
                        style={{ color: 'var(--muted-foreground)' }}
                    >
                        <X size={16} />
                    </button>
                </div>

                {/* Amount input */}
                <div className="space-y-2">
                    <label className="text-xs font-medium" style={{ color: 'var(--foreground)' }}>
                        Enter Amount (₹)
                    </label>
                    <div className="relative">
                        <span
                            className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm font-bold font-mono"
                            style={{ color: 'var(--primary)' }}
                        >
                            ₹
                        </span>
                        <input
                            ref={inputRef}
                            id="wallet-amount-input"
                            type="number"
                            min="1"
                            step="1"
                            value={amount}
                            onChange={e => { setAmount(e.target.value); setError(''); }}
                            onKeyDown={e => e.key === 'Enter' && handlePay()}
                            placeholder="0"
                            className="w-full pl-8 pr-4 py-3 rounded-xl text-sm font-mono font-semibold focus:outline-none focus:ring-1 transition-all"
                            style={{
                                background: 'var(--surface-2)',
                                border: `1px solid ${error ? 'var(--destructive)' : 'var(--border)'}`,
                                color: 'var(--foreground)',
                            }}
                        />
                    </div>
                    {error && (
                        <p className="text-xs flex items-center gap-1" style={{ color: 'var(--destructive)' }}>
                            <AlertCircle size={11} /> {error}
                        </p>
                    )}
                    <p className="text-[10px]" style={{ color: 'var(--muted-foreground)' }}>
                        Use Razorpay test card: 4111 1111 1111 1111, Exp: any future date, CVV: any 3 digits
                    </p>
                </div>

                {/* Actions */}
                <div className="flex gap-2.5">
                    <button
                        onClick={onClose}
                        className="flex-1 py-2.5 rounded-xl text-xs font-semibold border border-[var(--border)] hover:bg-[var(--surface-2)] transition-colors"
                        style={{ color: 'var(--foreground)' }}
                    >
                        Cancel
                    </button>
                    <button
                        id="pay-btn"
                        onClick={handlePay}
                        disabled={loading || !amount}
                        className="flex-1 py-2.5 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all hover:opacity-90 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                        style={{ background: 'var(--primary)', color: 'var(--primary-foreground)' }}
                    >
                        {loading ? <Loader2 size={13} className="animate-spin" /> : <Wallet size={13} />}
                        {loading ? 'Processing…' : 'Pay via Razorpay'}
                    </button>
                </div>
            </div>
        </div>
    );
}

function InvestmentsTable({ investments, loading }) {
    if (loading) {
        return (
            <div className="space-y-2">
                {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-14 rounded-xl shimmer" style={{ background: 'var(--surface-2)' }} />
                ))}
            </div>
        );
    }

    if (!investments || investments.length === 0) {
        return (
            <div className="glass rounded-2xl p-12 flex flex-col items-center justify-center gap-4 text-center">
                <div className="w-16 h-16 rounded-2xl flex items-center justify-center" style={{ background: 'var(--primary)/10' }}>
                    <BarChart2 size={28} style={{ color: 'var(--primary)' }} />
                </div>
                <div>
                    <h2 className="font-semibold" style={{ color: 'var(--foreground)' }}>No investments yet</h2>
                    <p className="text-sm mt-1 max-w-xs" style={{ color: 'var(--muted-foreground)' }}>
                        Complete a planning session and approve an investment plan to see your holdings here.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="glass rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr style={{ background: 'var(--surface-2)', borderBottom: '1px solid var(--border)' }}>
                            {['Source', 'Type', 'Invested', 'Holding', 'Years', 'Current Value', 'Gain', 'Bought'].map(h => (
                                <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                                    style={{ color: 'var(--muted-foreground)' }}>
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {investments.map((inv, idx) => {
                            const isGain = inv.gain >= 0;
                            return (
                                <tr
                                    key={inv.id}
                                    className="transition-colors hover:bg-[var(--surface-2)]/50"
                                    style={{ borderBottom: idx < investments.length - 1 ? '1px solid var(--border)' : 'none' }}
                                >
                                    {/* Source */}
                                    <td className="px-4 py-3.5">
                                        <div className="font-medium text-xs" style={{ color: 'var(--foreground)' }}>
                                            {inv.source}
                                        </div>
                                        {inv.notes && (
                                            <div className="text-[10px] mt-0.5 truncate max-w-[200px]"
                                                style={{ color: 'var(--muted-foreground)' }}>
                                                {inv.notes}
                                            </div>
                                        )}
                                    </td>

                                    {/* Asset type badge */}
                                    <td className="px-4 py-3.5">
                                        <span
                                            className="px-2 py-0.5 rounded-full text-[10px] font-semibold text-white"
                                            style={{ background: assetBadgeColor(inv.asset_type) }}
                                        >
                                            {assetLabel(inv.asset_type)}
                                        </span>
                                    </td>

                                    {/* Principal */}
                                    <td className="px-4 py-3.5 font-mono text-xs font-semibold" style={{ color: 'var(--foreground)' }}>
                                        {fmt(inv.principal)}
                                    </td>

                                    {/* Holding */}
                                    <td className="px-4 py-3.5 font-mono text-xs font-medium" style={{ color: 'var(--foreground)' }}>
                                        {inv.holding || `${inv.annual_rate_pct}% p.a.`}
                                    </td>

                                    {/* Years */}
                                    <td className="px-4 py-3.5 text-xs" style={{ color: 'var(--muted-foreground)' }}>
                                        {inv.years}y
                                    </td>

                                    {/* Current value */}
                                    <td className="px-4 py-3.5 font-mono text-xs font-semibold" style={{ color: 'var(--foreground)' }}>
                                        {fmt(inv.current_value)}
                                    </td>

                                    {/* Gain */}
                                    <td className="px-4 py-3.5">
                                        <div className="flex flex-col">
                                            <span className="font-mono text-xs font-semibold"
                                                style={{ color: isGain ? 'var(--gain)' : 'var(--loss)' }}>
                                                {isGain ? '+' : ''}{fmt(inv.gain)}
                                            </span>
                                            <span className="text-[10px]"
                                                style={{ color: isGain ? 'var(--gain)' : 'var(--loss)' }}>
                                                {fmtPct(inv.gain_pct)}
                                            </span>
                                        </div>
                                    </td>

                                    {/* Date */}
                                    <td className="px-4 py-3.5 text-[10px]" style={{ color: 'var(--muted-foreground)' }}>
                                        {new Date(inv.bought_at).toLocaleDateString('en-IN', {
                                            day: '2-digit', month: 'short', year: '2-digit',
                                        })}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

// ── Main Portfolio page ───────────────────────────────────────────────────────

export default function Portfolio() {
    const [summary, setSummary] = useState(null);
    const [investments, setInvestments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [showAddMoney, setShowAddMoney] = useState(false);
    const [toast, setToast] = useState(null);

    const showToast = (message, type = 'success') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 4000);
    };

    const fetchAll = useCallback(async (isRefresh = false) => {
        if (isRefresh) setRefreshing(true);
        else setLoading(true);
        try {
            const [summaryData, investmentsData] = await Promise.all([
                getPortfolioSummary(),
                getInvestments(),
            ]);
            setSummary(summaryData);
            setInvestments(investmentsData);
        } catch (err) {
            console.error('Portfolio fetch failed:', err);
            showToast('Failed to load portfolio data', 'error');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => { fetchAll(); }, [fetchAll]);

    const handleAddMoneySuccess = (newBalance) => {
        setShowAddMoney(false);
        setSummary(prev => prev ? { ...prev, wallet_balance: newBalance } : prev);
        showToast(`Wallet credited! New balance: ₹${newBalance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, 'success');
    };

    const gainColor = summary?.gain_loss >= 0 ? 'var(--gain)' : 'var(--loss)';

    return (
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-8 max-w-6xl mx-auto w-full space-y-8">

            {/* Page header */}
            <div className="flex items-start justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold gradient-text">Your Portfolio</h1>
                    <p className="text-sm mt-1" style={{ color: 'var(--muted-foreground)' }}>
                        Virtual investments made by Paisaan on your behalf.
                    </p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                        id="refresh-portfolio-btn"
                        onClick={() => fetchAll(true)}
                        disabled={refreshing || loading}
                        className="p-2 rounded-xl border border-[var(--border)] hover:bg-[var(--surface-2)] transition-colors disabled:opacity-50"
                        style={{ color: 'var(--muted-foreground)' }}
                        title="Refresh"
                    >
                        <RefreshCw size={15} className={refreshing ? 'animate-spin' : ''} />
                    </button>
                    <button
                        id="add-money-btn"
                        onClick={() => setShowAddMoney(true)}
                        className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all hover:opacity-90 active:scale-[0.98]"
                        style={{ background: 'var(--primary)', color: 'var(--primary-foreground)' }}
                    >
                        <Plus size={15} />
                        Add Money
                    </button>
                </div>
            </div>

            {/* Stat cards */}
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                <StatCard
                    label="Wallet Balance"
                    value={loading ? '—' : fmt(summary?.wallet_balance)}
                    subtext="Available to invest"
                    color="var(--primary)"
                    icon={Wallet}
                    pulse
                />
                <StatCard
                    label="Total Invested"
                    value={loading ? '—' : fmt(summary?.total_invested)}
                    subtext={`${summary?.investment_count ?? 0} investment${summary?.investment_count !== 1 ? 's' : ''}`}
                    icon={BarChart2}
                />
                <StatCard
                    label="Current Value"
                    value={loading ? '—' : fmt(summary?.current_value)}
                    subtext="Live estimate"
                    color={!loading && summary?.current_value > summary?.total_invested ? 'var(--gain)' : undefined}
                    icon={TrendingUp}
                />
                <StatCard
                    label="Gain / Loss"
                    value={loading ? '—' : fmt(summary?.gain_loss)}
                    subtext={loading ? '—' : fmtPct(summary?.gain_loss_pct)}
                    color={!loading ? gainColor : undefined}
                    icon={summary?.gain_loss >= 0 ? TrendingUp : TrendingDown}
                />
                <StatCard
                    label="Return"
                    value={loading ? '—' : fmtPct(summary?.gain_loss_pct)}
                    subtext="All time"
                    color={!loading ? gainColor : undefined}
                    icon={ArrowUpRight}
                />
            </div>

            {/* Investments table */}
            <div className="space-y-3">
                <div className="flex items-center gap-2">
                    <TrendingUp size={15} style={{ color: 'var(--primary)' }} />
                    <h2 className="text-sm font-semibold" style={{ color: 'var(--foreground)' }}>
                        Investment Holdings
                    </h2>
                    {investments.length > 0 && (
                        <span
                            className="ml-1 px-2 py-0.5 rounded-full text-[10px] font-bold"
                            style={{ background: 'var(--primary)/15', color: 'var(--primary)' }}
                        >
                            {investments.length}
                        </span>
                    )}
                </div>
                <InvestmentsTable investments={investments} loading={loading} />
            </div>

            {/* Add money modal */}
            {showAddMoney && (
                <AddMoneyModal
                    onClose={() => setShowAddMoney(false)}
                    onSuccess={handleAddMoneySuccess}
                />
            )}

            {/* Toast */}
            {toast && (
                <div className="fixed bottom-6 right-6 z-50 glass border border-[var(--border)] px-4 py-3 rounded-xl shadow-lg flex items-center gap-2.5 animate-bubble-in text-xs font-semibold max-w-sm">
                    {toast.type === 'error'
                        ? <AlertCircle size={14} className="flex-shrink-0" style={{ color: 'var(--destructive)' }} />
                        : <CheckCircle2 size={14} className="flex-shrink-0" style={{ color: 'var(--gain)' }} />
                    }
                    <span style={{ color: 'var(--foreground)' }}>{toast.message}</span>
                </div>
            )}
        </div>
    );
}
