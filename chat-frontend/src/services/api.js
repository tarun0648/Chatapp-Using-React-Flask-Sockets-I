// frontend/src/services/api.js - ADDED LOGOUT ENDPOINT
const API_BASE = 'http://localhost:5000';

export const api = {
  // Auth endpoints
  login: async (credentials) => {
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials)
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Login failed');
      return data;
    } catch (error) {
      console.error('API: Login error:', error);
      throw error;
    }
  },

  signup: async (userData) => {
    try {
      const response = await fetch(`${API_BASE}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Signup failed');
      return data;
    } catch (error) {
      console.error('API: Signup error:', error);
      throw error;
    }
  },

  // ✅ NEW: Logout endpoint
  logout: async (userId) => {
    try {
      const response = await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Logout failed');
      return data;
    } catch (error) {
      console.error('API: Logout error:', error);
      throw error;
    }
  },

  // User endpoints
  getProfile: async (token) => {
    try {
      const response = await fetch(`${API_BASE}/user/profile/${token}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to get profile');
      return data;
    } catch (error) {
      console.error('API: Profile error:', error);
      throw error;
    }
  },

  updateProfile: async (userId, profileData) => {
    try {
      const response = await fetch(`${API_BASE}/user/profile/${userId}/update`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profileData)
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to update profile');
      return data;
    } catch (error) {
      console.error('API: Update profile error:', error);
      throw error;
    }
  },

  getChats: async (userId) => {
    try {
      const response = await fetch(`${API_BASE}/user/chats/${userId}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to get chats');
      return data;
    } catch (error) {
      console.error('API: Chats error:', error);
      throw error;
    }
  },

  // Chat endpoints
  getMessages: async (chatId) => {
    try {
      const response = await fetch(`${API_BASE}/chat/${chatId}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to get messages');
      return data;
    } catch (error) {
      console.error('API: Messages error:', error);
      throw error;
    }
  },

  sendMessage: async (messageData) => {
    try {
      const response = await fetch(`${API_BASE}/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(messageData)
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to send message');
      return data;
    } catch (error) {
      console.error('API: Send message error:', error);
      throw error;
    }
  },

  markMessagesAsRead: async (readData) => {
    try {
      const response = await fetch(`${API_BASE}/chat/mark-read`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(readData)
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to mark messages as read');
      return data;
    } catch (error) {
      console.error('API: Mark read error:', error);
      throw error;
    }
  },

  // Group endpoints
  createGroup: async (groupData) => {
    try {
      const response = await fetch(`${API_BASE}/group/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(groupData)
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to create group');
      return data;
    } catch (error) {
      console.error('API: Create group error:', error);
      throw error;
    }
  },

  getUserGroups: async (userId) => {
    try {
      const response = await fetch(`${API_BASE}/group/user/${userId}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to get groups');
      return data;
    } catch (error) {
      console.error('API: Get groups error:', error);
      throw error;
    }
  },

  getGroupMessages: async (groupId) => {
    try {
      const response = await fetch(`${API_BASE}/group/${groupId}/messages`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to get group messages');
      return data;
    } catch (error) {
      console.error('API: Group messages error:', error);
      throw error;
    }
  },

  getGroupMembers: async (groupId) => {
    try {
      const response = await fetch(`${API_BASE}/group/${groupId}/members`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to get group members');
      return data;
    } catch (error) {
      console.error('API: Group members error:', error);
      throw error;
    }
  },

  addGroupMember: async (groupId, userId) => {
    try {
      const response = await fetch(`${API_BASE}/group/${groupId}/add-member`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          user_id: userId, 
          added_by: parseInt(localStorage.getItem('token')) 
        })
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to add member');
      return data;
    } catch (error) {
      console.error('API: Add member error:', error);
      throw error;
    }
  },

  searchUsersForGroup: async (groupId, searchTerm) => {
    try {
      const response = await fetch(`${API_BASE}/group/${groupId}/search-users?search=${encodeURIComponent(searchTerm)}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to search users');
      return data;
    } catch (error) {
      console.error('API: Search users error:', error);
      throw error;
    }
  },

  markGroupMessagesAsRead: async (groupId, userId) => {
    try {
      const response = await fetch(`${API_BASE}/group/${groupId}/mark-read`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to mark messages as read');
      return data;
    } catch (error) {
      console.error('API: Mark group read error:', error);
      throw error;
    }
  }
};