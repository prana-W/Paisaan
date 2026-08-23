import { NavLink } from 'react-router-dom';
import { TrendingUp, BarChart2, MessageSquare } from 'lucide-react';

const Header = () => {
    return (
        <header className="border-b flex-shrink-0 z-10"
            style={{ background: 'var(--card)', borderColor: 'var(--border)' }}>
            <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
                <NavLink to="/" id="header-brand" className="flex items-center gap-2 group">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center shadow-lg"
                        style={{ background: 'var(--primary)' }}>
                        <TrendingUp size={16} style={{ color: 'var(--primary-foreground)' }} />
                    </div>
                    <span className="font-bold text-lg gradient-text tracking-tight">Paisaan</span>
                </NavLink>

                <nav className="flex items-center gap-1" aria-label="Main navigation">
                    {[
                        { to: '/', id: 'nav-chat', icon: MessageSquare, label: 'Chat', end: true },
                        { to: '/portfolio', id: 'nav-portfolio', icon: BarChart2, label: 'Portfolio' },
                    ].map(({ to, id, icon: Icon, label, end }) => (
                        <NavLink
                            key={id}
                            id={id}
                            to={to}
                            end={end}
                            className={({ isActive }) =>
                                `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${isActive ? 'active-nav' : ''}`
                            }
                            style={({ isActive }) => ({
                                background: isActive ? 'var(--primary)/10' : 'transparent',
                                color: isActive ? 'var(--primary)' : 'var(--muted-foreground)',
                            })}
                        >
                            <Icon size={14} />
                            {label}
                        </NavLink>
                    ))}
                </nav>
            </div>
        </header>
    );
};

export default Header;
