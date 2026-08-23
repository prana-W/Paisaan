import {createRoot} from 'react-dom/client';
import App from './App.jsx';
import './index.css';
import {Toaster} from '@/components/ui/sonner';
import handleError from '@/utils/errorHandler';
import { SocketProvider } from "./context/socketContent.jsx";

window.onerror = (msg, src, line, col, error) => {
    handleError(error || msg, 'Global Error');
    return true;
};

window.onunhandledrejection = (event) => {
    handleError(event.reason, 'Unhandled Promise');
};

createRoot(document.getElementById('root')).render(
    <>
        <SocketProvider>
        <App />
        <Toaster richColors position="bottom-right" />
        </SocketProvider>
    </>
);
