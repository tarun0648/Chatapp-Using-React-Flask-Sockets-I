import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Phone, Video, MoreVertical, MessageCircle, Check, CheckCheck, Moon, Sun, Users, Info, UserPlus } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { api } from '../../services/api';
import { initSocket } from '../../services/socket';
import MessageInput from './MessageInput';
import GroupMemberModal from './GroupMemberModal';

const ChatRoom = () => {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const [messages, setMessages] = useState([]);
  const [currentChat, setCurrentChat] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isTyping, setIsTyping] = useState(false);
  const [onlineStatus, setOnlineStatus] = useState(false);
  const [groupMembers, setGroupMembers] = useState([]);
  const [showGroupInfo, setShowGroupInfo] = useState(false);
  const [showAddMember, setShowAddMember] = useState(false);
  const socketRef = useRef(null);
  const messagesEndRef = useRef(null);
  const processedMessageIds = useRef(new Set());

  const isGroupChat = chatId.startsWith('group_');
  const groupId = isGroupChat ? chatId.split('_')[1] : null;

  useEffect(() => {
    if (chatId && user) {
      loadMessages();
      setupSocket();
      
      if (isGroupChat) {
        loadGroupInfo();
      } else {
        const userIds = chatId.split('_');
        const otherUserId = userIds.find(id => id !== user.id.toString());
        fetchChatPartner(otherUserId);
      }
    }

    return () => {
      if (socketRef.current) {
        socketRef.current.emit('leave', { chat_id: chatId });
        socketRef.current.off('receive_message');
        socketRef.current.off('message_delivered');
        socketRef.current.off('messages_read');
        socketRef.current.off('user_typing');
        socketRef.current.off('user_online');
        socketRef.current.off('user_offline');
      }
    };
  }, [chatId, user]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadGroupInfo = async () => {
    try {
      const membersResponse = await api.getGroupMembers(groupId);
      if (membersResponse.success) {
        setGroupMembers(membersResponse.data);
        const groupInfo = {
          id: chatId,
          user: membersResponse.data[0]?.name || 'Group Chat',
          type: 'group',
          member_count: membersResponse.data.length
        };
        setCurrentChat(groupInfo);
      }
    } catch (error) {
      console.error('Failed to load group info:', error);
    }
  };

  const fetchChatPartner = async (userId) => {
    try {
      const response = await api.getProfile(userId);
      if (response.success) {
        setCurrentChat({
          id: chatId,
          user: response.data.name,
          user_id: userId,
          online: response.data.is_online || false,
          profile_picture: response.data.profile_picture,
          type: 'direct'
        });
        setOnlineStatus(response.data.is_online || false);
      }
    } catch (error) {
      console.error('Failed to fetch chat partner:', error);
      setCurrentChat({
        id: chatId,
        user: 'Chat Partner',
        user_id: userId,
        online: false,
        type: 'direct'
      });
    }
  };

  const setupSocket = () => {
    socketRef.current = initSocket();
    socketRef.current.auth = { token: user.id };
    
    if (!socketRef.current.connected) {
      socketRef.current.connect();
    }
    
    // Clear processed message IDs when joining a new chat
    processedMessageIds.current.clear();
    
    socketRef.current.emit('join', { chat_id: chatId });
    
    socketRef.current.on('receive_message', (data) => {
      console.log('Received message:', data);
      
      // Prevent duplicate messages
      if (processedMessageIds.current.has(data.id)) {
        console.log('Duplicate message detected, skipping:', data.id);
        return;
      }
      
      processedMessageIds.current.add(data.id);
      
      setMessages(prev => {
        // Double check for duplicates in the state
        const exists = prev.find(msg => msg.id === data.id);
        if (exists) {
          console.log('Message already exists in state:', data.id);
          return prev;
        }
        return [...prev, data];
      });
      
      // Mark as read if not from current user
      if (data.sender_id !== user.id) {
        setTimeout(() => {
          if (isGroupChat) {
            markGroupMessagesAsRead();
          } else {
            markMessagesAsRead(data.sender_id);
          }
        }, 100);
      }
    });

    socketRef.current.on('message_delivered', (data) => {
      setMessages(prev => 
        prev.map(msg => 
          msg.id === data.message_id 
            ? { ...msg, status: 'delivered' }
            : msg
        )
      );
    });

    socketRef.current.on('messages_read', (data) => {
      setMessages(prev => 
        prev.map(msg => 
          msg.sender_id === user.id 
            ? { ...msg, status: 'read' }
            : msg
        )
      );
    });

    socketRef.current.on('user_typing', (data) => {
      if (data.user_id !== user.id) {
        setIsTyping(data.is_typing);
        if (data.is_typing) {
          setTimeout(() => setIsTyping(false), 3000);
        }
      }
    });

    socketRef.current.on('user_online', (data) => {
      if (!isGroupChat) {
        const userIds = chatId.split('_');
        const otherUserId = parseInt(userIds.find(id => id !== user.id.toString()));
        if (data.user_id === otherUserId) {
          setOnlineStatus(true);
          setCurrentChat(prev => prev ? { ...prev, online: true } : prev);
        }
      }
    });

    socketRef.current.on('user_offline', (data) => {
      if (!isGroupChat) {
        const userIds = chatId.split('_');
        const otherUserId = parseInt(userIds.find(id => id !== user.id.toString()));
        if (data.user_id === otherUserId) {
          setOnlineStatus(false);
          setCurrentChat(prev => prev ? { ...prev, online: false } : prev);
        }
      }
    });
  };

  const loadMessages = async () => {
    try {
      let response;
      if (isGroupChat) {
        response = await api.getGroupMessages(groupId);
      } else {
        response = await api.getMessages(chatId);
      }
      
      if (response.success) {
        setMessages(response.data);
        
        // Add message IDs to processed set
        response.data.forEach(msg => {
          processedMessageIds.current.add(msg.id);
        });
        
        if (isGroupChat) {
          markGroupMessagesAsRead();
        } else {
          const userIds = chatId.split('_');
          const otherUserId = parseInt(userIds.find(id => id !== user.id.toString()));
          markMessagesAsRead(otherUserId);
        }
      }
    } catch (error) {
      console.error('Failed to load messages:', error);
    } finally {
      setLoading(false);
    }
  };

  const markMessagesAsRead = async (senderId) => {
    try {
      await api.markMessagesAsRead({
        sender_id: senderId,
        receiver_id: user.id,
        reader_id: user.id
      });

      if (socketRef.current) {
        socketRef.current.emit('mark_read', {
          sender_id: senderId,
          receiver_id: user.id,
          reader_id: user.id
        });
      }
    } catch (error) {
      console.error('Failed to mark messages as read:', error);
    }
  };

  const markGroupMessagesAsRead = async () => {
    try {
      await api.markGroupMessagesAsRead(groupId, user.id);
      
      if (socketRef.current) {
        socketRef.current.emit('mark_read', {
          group_id: groupId,
          reader_id: user.id
        });
      }
    } catch (error) {
      console.error('Failed to mark group messages as read:', error);
    }
  };

  const sendMessage = async (content) => {
    if (!content.trim() || !user) return;

    let messageData;
    
    if (isGroupChat) {
      messageData = {
        sender_id: user.id,
        content: content.trim(),
        group_id: parseInt(groupId),
        chat_id: chatId
      };
    } else {
      const chatParts = chatId.split('_');
      const receiverId = chatParts.find(id => id !== user.id.toString());
      
      messageData = {
        sender_id: user.id,
        receiver_id: parseInt(receiverId),
        content: content.trim(),
        chat_id: chatId
      };
    }

    try {
      // Don't wait for API response, let socket handle the message
      if (socketRef.current) {
        socketRef.current.emit('send_message', messageData);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const handleTyping = (isTyping) => {
    if (socketRef.current) {
      socketRef.current.emit('typing', {
        chat_id: chatId,
        user_id: user.id,
        is_typing: isTyping
      });
    }
  };

  const getMessageStatusIcon = (message) => {
    if (message.sender_id !== user.id) return null;
    
    switch (message.status) {
      case 'read':
        return <CheckCheck size={16} className="text-blue-500" />;
      case 'delivered':
        return <CheckCheck size={16} className="text-gray-400" />;
      case 'sent':
      default:
        return <Check size={16} className="text-gray-400" />;
    }
  };

  const getMessageAvatar = (message) => {
    if (message.sender_picture) {
      const imageSrc = message.sender_picture.startsWith('http') 
        ? message.sender_picture 
        : `http://localhost:5000${message.sender_picture}`;
      
      return (
        <img 
          src={imageSrc}
          alt={message.sender_name}
          className="w-8 h-8 rounded-full object-cover"
        />
      );
    }
    
    return (
      <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
        <span className="text-white text-sm font-semibold">
          {(message.sender_name || message.sender_username || 'U').charAt(0).toUpperCase()}
        </span>
      </div>
    );
  };

  const getChatAvatar = () => {
    if (isGroupChat) {
      return (
        <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-pink-600 rounded-full flex items-center justify-center">
          <Users className="text-white text-lg" />
        </div>
      );
    } else if (currentChat?.profile_picture) {
      const imageSrc = currentChat.profile_picture.startsWith('http') 
        ? currentChat.profile_picture 
        : `http://localhost:5000${currentChat.profile_picture}`;
      
      return (
        <img 
          src={imageSrc}
          alt={currentChat.user}
          className="w-10 h-10 rounded-full object-cover"
        />
      );
    } else {
      return (
        <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
          <span className="text-white font-semibold">
            {currentChat?.user?.charAt(0).toUpperCase() || 'U'}
          </span>
        </div>
      );
    }
  };

  const GroupInfoModal = () => {
    if (!showGroupInfo || !isGroupChat) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-md p-6 max-h-[80vh] overflow-y-auto">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Group Info</h2>
            <button
              onClick={() => setShowGroupInfo(false)}
              className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            >
              ✕
            </button>
          </div>

          <div className="text-center mb-6">
            <div className="w-20 h-20 bg-gradient-to-r from-purple-500 to-pink-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <Users className="text-white text-2xl" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {currentChat?.user}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {groupMembers.length} members
            </p>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold text-gray-900 dark:text-gray-100">Members</h4>
              <button
                onClick={() => {
                  setShowGroupInfo(false);
                  setShowAddMember(true);
                }}
                className="p-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900 rounded-lg transition"
                title="Add Member"
              >
                <UserPlus size={16} />
              </button>
            </div>
            
            {groupMembers.map((member) => {
              const memberAvatar = member.profile_picture ? (
                <img 
                  src={member.profile_picture.startsWith('http') ? member.profile_picture : `http://localhost:5000${member.profile_picture}`}
                  alt={member.name}
                  className="w-10 h-10 rounded-full object-cover"
                />
              ) : (
                <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                  <span className="text-white font-semibold">
                    {member.name.charAt(0).toUpperCase()}
                  </span>
                </div>
              );

              return (
                <div key={member.id} className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">
                  {memberAvatar}
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {member.name}
                      {member.role === 'admin' && (
                        <span className="ml-2 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-1 rounded">
                          Admin
                        </span>
                      )}
                    </p>
                    <p className="text-xs text-gray-600 dark:text-gray-400">@{member.username}</p>
                  </div>
                  {member.is_online && (
                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="h-screen bg-white dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading messages...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-white dark:bg-gray-900 flex flex-col">
      {/* Chat Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => navigate('/chats')}
              className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition lg:hidden"
            >
              <ArrowLeft size={20} />
            </button>
            <div className="relative">
              {getChatAvatar()}
              {!isGroupChat && onlineStatus && (
                <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 rounded-full border border-white dark:border-gray-800"></div>
              )}
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {currentChat?.user || 'Chat'}
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {isTyping ? 'Someone is typing...' : 
                 isGroupChat ? `${currentChat?.member_count || 0} members` :
                 (onlineStatus ? 'Online' : 'Offline')}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {isGroupChat && (
              <>
                <button 
                  onClick={() => setShowAddMember(true)}
                  className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
                  title="Add Member"
                >
                  <UserPlus size={20} />
                </button>
                <button 
                  onClick={() => setShowGroupInfo(true)}
                  className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
                >
                  <Info size={20} />
                </button>
              </>
            )}
            <button 
              onClick={toggleTheme}
              className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
            >
              {isDark ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <button className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition">
              <Phone size={20} />
            </button>
            <button className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition">
              <Video size={20} />
            </button>
            <button className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition">
              <MoreVertical size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50 dark:bg-gray-900">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-500 dark:text-gray-400">
              <MessageCircle size={48} className="mx-auto mb-4" />
              <p className="text-lg font-medium">No messages yet</p>
              <p className="text-sm">
                {isGroupChat ? 'Start the group conversation!' : 'Send a message to start the conversation'}
              </p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender_id === user?.id ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex items-end space-x-2 max-w-xs lg:max-w-md ${message.sender_id === user?.id ? 'flex-row-reverse space-x-reverse' : ''}`}>
                {/* Avatar for group messages from others */}
                {isGroupChat && message.sender_id !== user?.id && (
                  <div className="flex-shrink-0">
                    {getMessageAvatar(message)}
                  </div>
                )}
                
                <div
                  className={`px-4 py-2 rounded-2xl relative ${
                    message.sender_id === user?.id
                      ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white'
                      : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700'
                  }`}
                >
                  {/* Sender name for group messages */}
                  {isGroupChat && message.sender_id !== user?.id && (
                    <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                      {message.sender_name || message.sender_username}
                    </p>
                  )}
                  
                  <p className="text-sm">{message.content}</p>
                  
                  {/* Message status - only for own messages */}
                  {message.sender_id === user?.id && (
                    <div className="flex justify-end mt-1">
                      {getMessageStatusIcon(message)}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        
        {/* Typing indicator */}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-2 rounded-2xl">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Message Input */}
      <MessageInput onSendMessage={sendMessage} onTyping={handleTyping} />
      
      {/* Group Info Modal */}
      <GroupInfoModal />
      
      {/* Add Member Modal */}
      {showAddMember && (
        <GroupMemberModal
          groupId={groupId}
          onClose={() => setShowAddMember(false)}
          onMemberAdded={loadGroupInfo}
        />
      )}
    </div>
  );
};

export default ChatRoom;