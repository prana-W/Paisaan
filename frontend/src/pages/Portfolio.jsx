import { TrendingUp, BarChart2, Clock } from 'lucide-react';

/* ── Placeholder stat card ─────────────────────────────────────────────────── */
function StatCard({ label, value, subtext, colorClass = 'text-foreground' }) {
    return (
        <div className="glass rounded-2xl p-5 space-y-1">
            <p className="text-xs text-muted-foreground uppercase tracking-wider">{label}</p>
            <p className={`text-2xl font-bold font-mono ${colorClass}`}>{value}</p>
            {subtext && <p className="text-xs text-muted-foreground">{subtext}</p>}
        </div>
    );
}

export default function Portfolio() {
    return (
        <div className="flex-1 px-6 py-8 max-w-4xl mx-auto w-full space-y-8">

            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold gradient-text">Your Portfolio</h1>
                <p className="text-sm text-muted-foreground mt-1">
                    Simulation only — tracks how Paisaan's recommendations would have performed.
                </p>
            </div>

            {/* Summary stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                    label="Invested"
                    value="₹0"
                    subtext="No holdings yet"
                />
                <StatCard
                    label="Current Value"
                    value="₹0"
                    subtext="—"
                />
                <StatCard
                    label="Gain / Loss"
                    value="₹0"
                    subtext="—"
                    colorClass="text-muted-foreground"
                />
                <StatCard
                    label="Return"
                    value="0.00%"
                    subtext="All time"
                    colorClass="text-muted-foreground"
                />
            </div>

            {/* Empty state */}
            <div className="glass rounded-2xl p-12 flex flex-col items-center justify-center gap-4 text-center">
                <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
                    <BarChart2 size={28} className="text-primary" />
                </div>
                <div>
                    <h2 className="font-semibold text-foreground">No holdings yet</h2>
                    <p className="text-sm text-muted-foreground mt-1 max-w-xs">
                        Complete a planning session in the Chat tab to get your first investment allocation.
                    </p>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Clock size={12} />
                    Portfolio tracking launches in Phase 7
                </div>
            </div>

            {/* Timeline placeholder */}
            <div className="glass rounded-2xl p-6 space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                    <TrendingUp size={15} className="text-primary" />
                    Performance history
                </div>
                <div className="h-32 rounded-xl bg-surface-2 shimmer" />
            </div>
        </div>
    );
}
