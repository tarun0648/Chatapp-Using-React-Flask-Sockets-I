// frontend/src/components/chat/ChatList.js - ENHANCED LOGOUT HANDLING
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Settings, LogOut, Search, MessageCircle, Moon, Sun, Wifi, WifiOff, Users, Plus } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { api } from '../../services/api';
import { initSocket } from '../../services/socket';

const ChatList = () => {
  const [chats, setChats] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState(new Set());
  const [socketConnected, setSocketConnected] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();

  useEffect(() => {
    loadChats();
    setupSocket();
  }, [user]);

  const setupSocket = () => {
    if (!user) return;
    
    const socket = initSocket();
    socket.auth = { token: user.id };
    
    if (!socket.connected) {
      socket.connect();
    }

    // Connection status tracking
    socket.on('connect', () => {
      console.log('🔌 ChatList: Socket connected');
      setSocketConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('🔌 ChatList: Socket disconnected');
      setSocketConnected(false);
    });

    // Enhanced online status with immediate updates
    socket.on('user_online', (data) => {
      console.log('🟢 User came online:', data);
      setOnlineUsers(prev => new Set([...prev, data.user_id]));
      
      // Update chat list to reflect online status immediately
      setChats(prev => prev.map(chat => 
        chat.user_id === data.user_id 
          ? { ...chat, online: true, status: 'Online' }
          : chat
      ));
    });
    
    socket.on('user_offline', (data) => {
      console.log('🔴 User went offline:', data);
      setOnlineUsers(prev => {
        const newSet = new Set(prev);
        newSet.delete(data.user_id);
        return newSet;
      });
      
      // Update chat list to reflect offline status immediately
      setChats(prev => prev.map(chat => 
        chat.user_id === data.user_id 
          ? { ...chat, online: false, status: 'Offline' }
          : chat
      ));
    });

    // Enhanced new message notifications for ChatList
    socket.on('new_message_notification', (data) => {
      console.log('📢 NEW MESSAGE NOTIFICATION:', data);
      
      // Update chat list with new message preview and unread count
      setChats(prev => prev.map(chat => {
        const chatMatches = (
          (chat.type === 'direct' && chat.id === data.chat_id) ||
          (chat.type === 'group' && chat.id === `group_${data.group_id}`) ||
          (chat.id === data.chat_id)
        );
        
        if (chatMatches && data.sender_id !== user.id) {
          const truncatedContent = data.content.length > 50 ? 
            data.content.substring(0, 50) + '...' : 
            data.content;
          
          return {
            ...chat,
            last_message: data.content,
            last_message_preview: truncatedContent,
            unread_count: (chat.unread_count || 0) + 1,
            timestamp: 'now',
            last_sender: data.sender_name
          };
        }
        return chat;
      }));
      
      // Show visual notification
      showNotification(data);
    });

    // Real-time message updates for chat list
    socket.on('receive_message', (data) => {
      console.log('📨 ChatList: Received message update:', data);
      
      // Update chat list with new message preview and unread count
      setChats(prev => prev.map(chat => {
        const chatMatches = (chat.type === 'direct' && chat.id === data.chat_id) ||
                           (chat.type === 'group' && chat.id === `group_${data.group_id}`);
        
        if (chatMatches && data.sender_id !== user.id) {
          const truncatedContent = data.content.length > 50 ? 
            data.content.substring(0, 50) + '...' : 
            data.content;
          
          return {
            ...chat,
            last_message: data.content,
            last_message_preview: truncatedContent,
            unread_count: (chat.unread_count || 0) + 1,
            timestamp: 'now',
            last_sender: data.sender_name
          };
        }
        return chat;
      }));
    });

    return () => {
      socket.off('connect');
      socket.off('disconnect');
      socket.off('user_online');
      socket.off('user_offline');
      socket.off('new_message_notification');
      socket.off('receive_message');
    };
  };

  // Visual notification function
  const showNotification = (data) => {
    // Browser notification (if permission granted)
    if (Notification.permission === 'granted') {
      new Notification(`New message from ${data.sender_name}`, {
        body: data.content,
        icon: '/favicon.ico',
        tag: data.chat_id
      });
    }
    
    // Visual flash effect
    document.title = `💬 New Message - ChatApp`;
    setTimeout(() => {
      document.title = 'ChatApp';
    }, 3000);
  };

  // Request notification permission on mount
  useEffect(() => {
    if (Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  const loadChats = async () => {
    if (!user) return;
    
    try {
      const response = await api.getChats(user.id);
      if (response.success) {
        setChats(response.data.chats || response.data);
        setCurrentUser(response.data.current_user || user);
        
        const online = new Set(
          (response.data.chats || response.data)
            .filter(chat => chat.type === 'direct' && chat.online)
            .map(chat => chat.user_id)
        );
        setOnlineUsers(online);
      }
    } catch (error) {
      console.error('Failed to load chats:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredChats = chats.filter(chat => 
    chat.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (chat.username && chat.username.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (chat.description && chat.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const openChat = (chat) => {
    // Reset unread count when opening chat
    setChats(prev => prev.map(c => 
      c.id === chat.id ? { ...c, unread_count: 0 } : c
    ));
    navigate(`/chat/${chat.id}`);
  };

  // ✅ ENHANCED: Logout with visual feedback
  const handleLogout = async () => {
    if (loggingOut) return;
    
    setLoggingOut(true);
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setLoggingOut(false);
    }
  };

  const getStatusColor = (chat) => {
    if (chat.type === 'group') return 'bg-blue-500';
    if (onlineUsers.has(chat.user_id) || chat.online) return 'bg-green-500';
    return 'bg-gray-400 dark:bg-gray-600';
  };

  const getStatusText = (chat) => {
    if (chat.type === 'group') {
      return `${chat.member_count} members`;
    }
    if (onlineUsers.has(chat.user_id) || chat.online) {
      return 'Online';
    }
    return chat.status || 'Offline';
  };

  const getAvatar = (chat) => {
    if (chat.profile_picture) {
      const imageSrc = chat.profile_picture.startsWith('http') 
        ? chat.profile_picture 
        : `http://localhost:5000${chat.profile_picture}`;
      
      return (
        <img 
          src={imageSrc}
          alt={chat.user}
          className="w-12 h-12 rounded-full object-cover"
        />
      );
    }
    
    return (
      <div className={`w-12 h-12 ${chat.type === 'group' ? 'bg-gradient-to-r from-purple-500 to-pink-600' : 'bg-gradient-to-r from-blue-500 to-purple-600'} rounded-full flex items-center justify-center`}>
        {chat.type === 'group' ? (
          <Users className="text-white text-lg" />
        ) : (
          <span className="text-white font-semibold">
            {chat.user.charAt(0).toUpperCase()}
          </span>
        )}
      </div>
    );
  };

  const getUserAvatar = () => {
    if (currentUser?.profile_picture) {
      const imageSrc = currentUser.profile_picture.startsWith('http') 
        ? currentUser.profile_picture 
        : `http://localhost:5000${currentUser.profile_picture}`;
      
      return (
        <img 
          src={imageSrc}
          alt={currentUser.name}
          className="w-10 h-10 rounded-full object-cover"
        />
      );
    }
    
    return (
      <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
        <span className="text-white text-lg font-semibold">
          {(currentUser?.name || user?.name || 'U').charAt(0).toUpperCase()}
        </span>
      </div>
    );
  };

  const CreateGroupModal = () => {
    const [groupName, setGroupName] = useState('');
    const [groupDescription, setGroupDescription] = useState('');
    const [creating, setCreating] = useState(false);

    const handleCreateGroup = async (e) => {
      e.preventDefault();
      if (!groupName.trim()) return;

      setCreating(true);
      try {
        const response = await api.createGroup({
          name: groupName.trim(),
          description: groupDescription.trim(),
          created_by: user.id
        });

        if (response.success) {
          setShowGroupModal(false);
          setGroupName('');
          setGroupDescription('');
          loadChats();
        }
      } catch (error) {
        console.error('Failed to create group:', error);
      } finally {
        setCreating(false);
      }
    };

    if (!showGroupModal) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-md p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">Create New Group</h2>
          
          <form onSubmit={handleCreateGroup} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Group Name
              </label>
              <input
                type="text"
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                placeholder="Enter group name"
                required
                disabled={creating}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Description (Optional)
              </label>
              <textarea
                value={groupDescription}
                onChange={(e) => setGroupDescription(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                placeholder="Enter group description"
                rows={3}
                disabled={creating}
              />
            </div>

            <div className="flex space-x-3 pt-4">
              <button
                type="button"
                onClick={() => setShowGroupModal(false)}
                disabled={creating}
                className="flex-1 px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={creating || !groupName.trim()}
                className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:from-blue-600 hover:to-purple-700 transition disabled:opacity-50"
              >
                {creating ? 'Creating...' : 'Create Group'}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading chats...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getUserAvatar()}
            <div>
              <h1 className="text-xl font-semibold text-gray-800 dark:text-gray-100">Chats</h1>
              <p className="text-sm text-gray-600 dark:text-gray-400 flex items-center space-x-2">
                <span>Welcome back, {currentUser?.name || user?.name}</span>
                {socketConnected ? (
                  <span className="text-green-500 text-xs"></span>
                ) : (
                  <span className="text-red-500 text-xs"></span>
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button 
              onClick={() => setShowGroupModal(true)}
              className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
              title="Create Group"
              disabled={loggingOut}
            >
              <Plus size={20} />
            </button>
            <button 
              onClick={toggleTheme}
              className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
              disabled={loggingOut}
            >
              {isDark ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <button 
              onClick={() => navigate('/profile')}
              className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
              disabled={loggingOut}
            >
              <Settings size={20} />
            </button>
            <button 
              onClick={handleLogout}
              disabled={loggingOut}
              className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition disabled:opacity-50"
              title={loggingOut ? "Logging out..." : "Logout"}
            >
              {loggingOut ? (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-gray-600"></div>
              ) : (
                <LogOut size={20} />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            disabled={loggingOut}
          />
        </div>
      </div>

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto">
        {filteredChats.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
            <MessageCircle size={48} className="mb-4" />
            <p className="text-lg font-medium">No conversations yet</p>
            <p className="text-sm">Start a new chat or create a group</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {filteredChats.map((chat) => (
              <div
                key={chat.id}
                onClick={() => !loggingOut && openChat(chat)}
                className={`px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition ${
                  chat.unread_count > 0 ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                } ${loggingOut ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <div className="flex items-center space-x-3">
                  <div className="relative">
                    {getAvatar(chat)}
                    {chat.type === 'direct' && (
                      <div className={`absolute -bottom-1 -right-1 w-4 h-4 ${getStatusColor(chat)} rounded-full border-2 border-white dark:border-gray-800 ${
                        onlineUsers.has(chat.user_id) || chat.online ? 'animate-pulse' : ''
                      }`}></div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h3 className={`text-sm font-semibold ${chat.unread_count > 0 ? 'text-blue-600 dark:text-blue-400' : 'text-gray-900 dark:text-gray-100'} truncate`}>
                        {chat.user}
                        {chat.type === 'group' && chat.role === 'admin' && (
                          <span className="ml-2 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-1 rounded">
                            Admin
                          </span>
                        )}
                      </h3>
                      <div className="flex items-center space-x-2">
                        {chat.unread_count > 0 && (
                          <span className="bg-blue-500 text-white text-xs rounded-full px-2 py-1 min-w-[20px] text-center animate-pulse">
                            {chat.unread_count}
                          </span>
                        )}
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {chat.timestamp || 'Now'}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <p className={`text-sm ${chat.unread_count > 0 ? 'text-gray-800 dark:text-gray-200 font-medium' : 'text-gray-600 dark:text-gray-400'} truncate`}>
                        {chat.last_message_preview || 
                         (chat.type === 'group' ? chat.description || 'Group chat' : `@${chat.username}`)}
                      </p>
                      <div className="flex items-center space-x-1">
                        {chat.type === 'direct' && (
                          <>
                            {onlineUsers.has(chat.user_id) || chat.online ? (
                              <Wifi size={12} className="text-green-500" />
                            ) : (
                              <WifiOff size={12} className="text-gray-400" />
                            )}
                          </>
                        )}
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {getStatusText(chat)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Logout overlay */}
      {loggingOut && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 flex items-center space-x-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="text-gray-900 dark:text-gray-100">Logging out...</p>
          </div>
        </div>
      )}

      <CreateGroupModal />
    </div>
  );
};

export default ChatList;