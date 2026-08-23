import { NavLink } from 'react-router-dom';
import { TrendingUp, BarChart2, MessageSquare } from 'lucide-react';

const Header = () => {
    return (
        <header className="glass border-b border-border flex-shrink-0 z-10">
            <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">

                {/* Brand */}
                <NavLink to="/" className="flex items-center gap-2 group" id="header-brand">
                    <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-lg group-hover:shadow-primary/30 transition-shadow">
                        <TrendingUp size={16} className="text-primary-foreground" />
                    </div>
                    <span className="font-bold text-lg gradient-text tracking-tight">Paisaan</span>
                </NavLink>

                {/* Nav */}
                <nav className="flex items-center gap-1" aria-label="Main navigation">
                    <NavLink
                        id="nav-chat"
                        to="/"
                        end
                        className={({ isActive }) =>
                            `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                                isActive
                                    ? 'bg-primary/10 text-primary'
                                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                            }`
                        }
                    >
                        <MessageSquare size={14} />
                        Chat
                    </NavLink>
                    <NavLink
                        id="nav-portfolio"
                        to="/portfolio"
                        className={({ isActive }) =>
                            `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                                isActive
                                    ? 'bg-primary/10 text-primary'
                                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                            }`
                        }
                    >
                        <BarChart2 size={14} />
                        Portfolio
                    </NavLink>
                </nav>
            </div>
        </header>
    );
};

export default Header;
