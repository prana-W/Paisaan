import { TrendingUp, BarChart2, Clock } from 'lucide-react';

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
    return (
        <div className="flex-1 px-6 py-8 max-w-4xl mx-auto w-full space-y-8">
            <div>
                <h1 className="text-2xl font-bold gradient-text">Your Portfolio</h1>
                <p className="text-sm mt-1" style={{ color: 'var(--muted-foreground)' }}>
                    Simulation only — tracks how Paisaan's recommendations would have performed.
                </p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard label="Invested" value="₹0" subtext="No holdings yet" />
                <StatCard label="Current Value" value="₹0" subtext="—" />
                <StatCard label="Gain / Loss" value="₹0" subtext="—" colorVar="var(--muted-foreground)" />
                <StatCard label="Return" value="0.00%" subtext="All time" colorVar="var(--muted-foreground)" />
            </div>

            <div className="glass rounded-2xl p-12 flex flex-col items-center justify-center gap-4 text-center">
                <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
                    style={{ background: 'var(--primary)/10' }}>
                    <BarChart2 size={28} style={{ color: 'var(--primary)' }} />
                </div>
                <div>
                    <h2 className="font-semibold" style={{ color: 'var(--foreground)' }}>No holdings yet</h2>
                    <p className="text-sm mt-1 max-w-xs" style={{ color: 'var(--muted-foreground)' }}>
                        Complete a planning session in the Chat tab to get your first investment allocation.
                    </p>
                </div>
                <div className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--muted-foreground)' }}>
                    <Clock size={12} />
                    Portfolio tracking launches in Phase 7
                </div>
            </div>

            <div className="glass rounded-2xl p-6 space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium" style={{ color: 'var(--foreground)' }}>
                    <TrendingUp size={15} style={{ color: 'var(--primary)' }} />
                    Performance history
                </div>
                <div className="h-32 rounded-xl shimmer" style={{ background: 'var(--surface-2)' }} />
            </div>
        </div>
    );
}
