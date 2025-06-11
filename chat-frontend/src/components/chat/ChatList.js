import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Settings, LogOut, Search, MessageCircle, Moon, Sun, Wifi, WifiOff, Users, Plus } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { api } from '../../services/api';
import { initSocket } from '../../services/socket';

const ChatList = () => {
  const [chats, setChats] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState(new Set());
  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const loadChats = useCallback(async () => {
    if (!user) return;
    
    try {
      const response = await api.getChats(user.id);
      if (response.success) {
        setChats(response.data);
        const online = new Set(
          response.data
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
  }, [user]);

  const setupSocket = useCallback(() => {
    if (!user) return;
    
    const socket = initSocket();
    socket.auth = { token: user.id };
    socket.connect();
    
    socket.on('user_online', (data) => {
      setOnlineUsers(prev => new Set([...prev, data.user_id]));
    });
    
    socket.on('user_offline', (data) => {
      setOnlineUsers(prev => {
        const newSet = new Set(prev);
        newSet.delete(data.user_id);
        return newSet;
      });
    });

    socket.on('receive_message', () => {
      loadChats();
    });

    return () => {
      socket.disconnect();
    };
  }, [user, loadChats]);

  useEffect(() => {
    loadChats();
    const cleanup = setupSocket();
    return cleanup;
  }, [loadChats, setupSocket]);

  const filteredChats = chats.filter(chat => 
    chat.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (chat.username && chat.username.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (chat.description && chat.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const openChat = (chat) => {
    navigate(`/chat/${chat.id}`);
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
      return (
        <img 
          src={chat.profile_picture} 
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
        alert('Failed to create group. Please try again.');
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
                maxLength={50}
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
                maxLength={200}
              />
            </div>

            <div className="flex space-x-3 pt-4">
              <button
                type="button"
                onClick={() => setShowGroupModal(false)}
                disabled={creating}
                className="flex-1 px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={creating || !groupName.trim()}
                className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:from-blue-600 hover:to-purple-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {creating ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Creating...
                  </div>
                ) : (
                  'Create Group'
                )}
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
            <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
              <User className="text-white text-lg" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-800 dark:text-gray-100">Chats</h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">Welcome back, {user?.name}</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button 
              onClick={() => setShowGroupModal(true)}
              className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
              title="Create Group"
            >
              <Plus size={20} />
            </button>
            <button 
              onClick={toggleTheme}
              className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
              title="Toggle Theme"
            >
              {isDark ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <button 
              onClick={() => navigate('/profile')}
              className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
              title="Profile"
            >
              <Settings size={20} />
            </button>
            <button 
              onClick={logout}
              className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
              title="Logout"
            >
              <LogOut size={20} />
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
            <button
              onClick={() => setShowGroupModal(true)}
              className="mt-4 px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:from-blue-600 hover:to-purple-700 transition"
            >
              Create First Group
            </button>
          </div>
        ) : (
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {filteredChats.map((chat) => (
              <div
                key={chat.id}
                onClick={() => openChat(chat)}
                className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition"
              >
                <div className="flex items-center space-x-3">
                  <div className="relative flex-shrink-0">
                    {getAvatar(chat)}
                    {chat.type === 'direct' && (
                      <div className={`absolute -bottom-1 -right-1 w-4 h-4 ${getStatusColor(chat)} rounded-full border-2 border-white dark:border-gray-800`}></div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
                        {chat.user}
                        {chat.type === 'group' && chat.role === 'admin' && (
                          <span className="ml-2 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-1 rounded">
                            Admin
                          </span>
                        )}
                      </h3>
                      <div className="flex items-center space-x-2">
                        {chat.unread_count > 0 && (
                          <span className="bg-blue-500 text-white text-xs rounded-full px-2 py-1 min-w-[20px] text-center">
                            {chat.unread_count > 99 ? '99+' : chat.unread_count}
                          </span>
                        )}
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {chat.timestamp || 'Now'}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between mt-1">
                      <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
                        {chat.type === 'group' ? 
                          (chat.description || 'Group conversation') : 
                          `@${chat.username}`
                        }
                      </p>
                      <div className="flex items-center space-x-1 flex-shrink-0">
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

      <CreateGroupModal />
    </div>
  );
};

export default ChatList;