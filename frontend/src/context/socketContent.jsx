import React, { createContext, useEffect, useState } from "react";
import { io } from "socket.io-client";

const SocketContext = createContext(null);

export const SocketProvider = ({ children }) => {
    const [socket, setSocket] = useState(null);

    useEffect(() => {
        // Connect to backend
        const socketInstance = io(import.meta.env.VITE_SERVER_URL, {
            withCredentials: true,
            transports: ["websocket"],
        });

        setSocket(socketInstance);

        // Clean up when unmounted
        return () => {
            socketInstance.disconnect();
        };
    }, []);

    return (
        <SocketContext.Provider value={socket}>
            {children}
        </SocketContext.Provider>
    );
};

export {SocketContext}