import { NavLink, useLocation } from 'react-router-dom';
import { TrendingUp, BarChart2, MessageSquare, Menu } from 'lucide-react';

const Header = () => {
    const location = useLocation();
    const isChatPage = location.pathname === '/';

    return (
        <header className="w-full border-b flex-shrink-0 z-10"
            style={{ background: 'var(--card)', borderColor: 'var(--border)' }}>
            <div className="w-full px-4 h-14 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    {isChatPage && (
                        <button
                            onClick={() => window.dispatchEvent(new CustomEvent('toggle-sidebar'))}
                            className="p-1.5 rounded-lg hover:bg-[var(--surface-2)] text-[var(--muted-foreground)] flex-shrink-0"
                            title="Toggle Sidebar"
                        >
                            <Menu size={18} />
                        </button>
                    )}
                    <NavLink to="/" id="header-brand" className="flex items-center gap-2 group">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center shadow-lg"
                            style={{ background: 'var(--primary)' }}>
                            <TrendingUp size={16} style={{ color: 'var(--primary-foreground)' }} />
                        </div>
                        <span className="font-bold text-lg gradient-text tracking-tight">Paisaan</span>
                    </NavLink>
                </div>

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
