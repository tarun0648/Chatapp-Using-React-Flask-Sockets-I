// frontend/src/services/socket.js - ENHANCED WITH LOGOUT HANDLING
import { io } from 'socket.io-client';

let socket = null;

export const initSocket = () => {
  if (!socket || socket.disconnected) {
    socket = io('http://localhost:5000', {
      autoConnect: false,
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 20000,
      forceNew: false,
      upgrade: true,
      rememberUpgrade: true
    });

    socket.on('connect', () => {
      console.log('🔌 Socket connected:', socket.id);
    });

    socket.on('disconnect', (reason) => {
      console.log('🔌 Socket disconnected:', reason);
      if (reason === 'io server disconnect') {
        // the disconnection was initiated by the server, reconnect manually
        socket.connect();
      }
    });

    socket.on('connect_error', (error) => {
      console.error('❌ Socket connection error:', error);
    });

    socket.on('reconnect', (attemptNumber) => {
      console.log('🔄 Socket reconnected after', attemptNumber, 'attempts');
    });

    socket.on('reconnect_error', (error) => {
      console.error('❌ Socket reconnection error:', error);
    });

    socket.on('reconnect_failed', () => {
      console.error('❌ Socket reconnection failed');
    });

    // ✅ NEW: Handle logout confirmation
    socket.on('logout_confirmed', (data) => {
      console.log('🚪 Logout confirmed by server:', data);
    });

    // Add debug listeners for development
    if (process.env.NODE_ENV === 'development') {
      socket.onAny((event, ...args) => {
        console.log('📡 Socket event received:', event, args);
      });

      socket.onAnyOutgoing((event, ...args) => {
        console.log('📤 Socket event sent:', event, args);
      });
    }
  }
  
  return socket;
};

export const getSocket = () => {
  if (!socket) {
    return initSocket();
  }
  return socket;
};

// ✅ ENHANCED: Proper disconnect with cleanup
export const disconnectSocket = () => {
  if (socket) {
    console.log('🔌 Disconnecting socket properly...');
    
    // Remove all listeners to prevent memory leaks
    socket.removeAllListeners();
    
    // Disconnect the socket
    socket.disconnect();
    socket = null;
    
    console.log('✅ Socket disconnected and cleaned up');
  }
};

export const connectSocket = () => {
  if (socket && !socket.connected) {
    socket.connect();
  }
};

export const isSocketConnected = () => {
  return socket && socket.connected;
};

// ✅ NEW: Emit logout event
export const emitLogout = (userId) => {
  if (socket && socket.connected) {
    console.log('🚪 Emitting logout event for user:', userId);
    socket.emit('user_logout', { user_id: userId });
  }
};