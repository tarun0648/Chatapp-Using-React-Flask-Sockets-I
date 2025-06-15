// frontend/src/context/AuthContext.js - FIXED LOGOUT WITH SOCKET CLEANUP
import React, { createContext, useState, useContext, useEffect } from 'react';
import { api } from '../services/api';
import { disconnectSocket, getSocket } from '../services/socket';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    const token = localStorage.getItem('token');
    
    if (token) {
      try {
        await loadUserProfile(token);
      } catch (error) {
        console.error('Failed to load profile:', error);
        localStorage.removeItem('token');
        setIsAuthenticated(false);
        setUser(null);
      }
    }
    setLoading(false);
  };

  const loadUserProfile = async (token) => {
    try {
      const response = await api.getProfile(token);
      if (response.success) {
        setUser(response.data);
        setIsAuthenticated(true);
      } else {
        throw new Error('Failed to get profile');
      }
    } catch (error) {
      console.error('Profile load error:', error);
      localStorage.removeItem('token');
      setIsAuthenticated(false);
      setUser(null);
      throw error;
    }
  };

  const login = async (credentials) => {
    try {
      const response = await api.login(credentials);
      if (response.success && response.token) {
        localStorage.setItem('token', response.token);
        await loadUserProfile(response.token);
        return response;
      } else {
        throw new Error(response.message || 'Login failed');
      }
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const signup = async (userData) => {
    try {
      const response = await api.signup(userData);
      return response;
    } catch (error) {
      console.error('Signup error:', error);
      throw error;
    }
  };

  // ✅ FIXED: Enhanced logout with proper socket cleanup
  const logout = async () => {
    try {
      console.log('🚪 Starting logout process...');
      
      // 1. Get current socket before cleanup
      const socket = getSocket();
      
      // 2. Emit logout event to server BEFORE disconnecting
      if (socket && socket.connected && user) {
        console.log('📤 Emitting logout event for user:', user.id);
        socket.emit('user_logout', { user_id: user.id });
        
        // Give server time to process logout
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      
      // 3. Call API logout endpoint (if you have one)
      if (user) {
        try {
          await api.logout(user.id);
        } catch (error) {
          console.error('API logout error:', error);
          // Continue with logout even if API call fails
        }
      }
      
      // 4. Disconnect socket
      console.log('🔌 Disconnecting socket...');
      disconnectSocket();
      
      // 5. Clear local storage and state
      localStorage.removeItem('token');
      setUser(null);
      setIsAuthenticated(false);
      
      console.log('✅ Logout completed successfully');
      
    } catch (error) {
      console.error('❌ Logout error:', error);
      // Force logout even if there are errors
      disconnectSocket();
      localStorage.removeItem('token');
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  const updateUser = (updatedData) => {
    setUser(prev => ({ ...prev, ...updatedData }));
  };

  const value = {
    user,
    isAuthenticated,
    loading,
    login,
    signup,
    logout,
    updateUser
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};