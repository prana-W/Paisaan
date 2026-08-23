import {Chat, Portfolio} from './pages';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import { ThemeProvider } from "@/components/theme-provider";
import Layout from './Layout.jsx';

import {createBrowserRouter, RouterProvider} from 'react-router-dom';

const router = createBrowserRouter([
    {
        path: '/',
        element: <Layout />,
        children: [
            {
                path: '',
                element: <Chat />,
            },
            {
                path: 'portfolio',
                element: <Portfolio />,
            },
            {
                path: '*',
                element: (
                    <div className="flex-1 flex items-center justify-center">
                        <div className="text-center space-y-2">
                            <p className="text-4xl font-bold gradient-text">404</p>
                            <p className="text-muted-foreground text-sm">Page not found</p>
                        </div>
                    </div>
                ),
            },
        ],
    },
]);

function App() {
    return (
        <ThemeProvider defaultTheme="dark" storageKey="paisaan-theme">
            <ErrorBoundary>
                <RouterProvider router={router} />
            </ErrorBoundary>
        </ThemeProvider>
    );
}

export default App;
