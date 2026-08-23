/**
 * SocketContext — placeholder for Phase 0.
 *
 * Paisaan uses HTTP polling (POST /session → POST /resume) for the
 * interrupt/resume pattern. WebSocket support may be added in a later phase
 * for real-time portfolio price updates.
 *
 * For now this is a no-op context so main.jsx imports don't break.
 */
import React, { createContext } from "react";

const SocketContext = createContext(null);

export const SocketProvider = ({ children }) => {
    return (
        <SocketContext.Provider value={null}>
            {children}
        </SocketContext.Provider>
    );
};

export { SocketContext };