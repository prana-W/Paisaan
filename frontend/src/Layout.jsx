import {Outlet} from 'react-router-dom';
import {Header, Footer} from './components';
import {Toaster} from '@/components/ui/sonner';

function Layout() {
    return (
        <>
            <div className="min-h-screen h-screen flex flex-col bg-background">
                <Header />
                <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
                    <Outlet />
                </main>
            </div>
            <Toaster richColors position="bottom-right" />
        </>
    );
}

export default Layout;
