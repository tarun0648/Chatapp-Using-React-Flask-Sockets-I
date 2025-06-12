import React, { createContext, useState, useContext, useEffect } from 'react';
import { api } from '../services/api';

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

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    setIsAuthenticated(false);
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