import {SocketContext} from '../context/socketContent.jsx';
import {useContext} from 'react';

const useSocket = () => {
    return useContext(SocketContext);
};

export default useSocket;