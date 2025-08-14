// frontend/src/components/chat/ChatRoom.js - ENHANCED FOR REAL-TIME
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
  const [typingUsers, setTypingUsers] = useState(new Set());
  const [onlineStatus, setOnlineStatus] = useState(false);
  const [groupMembers, setGroupMembers] = useState([]);
  const [showGroupInfo, setShowGroupInfo] = useState(false);
  const [showAddMember, setShowAddMember] = useState(false);
  const socketRef = useRef(null);
  const messagesEndRef = useRef(null);
  const processedMessageIds = useRef(new Set());
  const roomJoinedRef = useRef(false);
  const normalizedChatId = useRef(null);
  const heartbeatInterval = useRef(null);

  const isGroupChat = chatId.startsWith('group_');
  const groupId = isGroupChat ? chatId.split('_')[1] : null;

  // Normalize chat ID for direct chats
  const getNormalizedChatId = () => {
    if (isGroupChat) {
      return chatId;
    }
    
    try {
      const userIds = chatId.split('_').map(id => parseInt(id)).filter(id => !isNaN(id));
      if (userIds.length === 2) {
        userIds.sort();
        return `${userIds[0]}_${userIds[1]}`;
      }
    } catch (error) {
      console.error('Error normalizing chat ID:', error);
    }
    
    return chatId;
  };

  useEffect(() => {
    if (chatId && user) {
      console.log(`🏠 Setting up chat room: ${chatId} for user: ${user.id}`);
      
      normalizedChatId.current = getNormalizedChatId();
      console.log(`📝 Normalized chat ID: ${normalizedChatId.current}`);
      
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
        console.log('🧹 Cleaning up chat room...');
        socketRef.current.emit('leave', { chat_id: normalizedChatId.current || chatId });
        
        // Remove all event listeners
        socketRef.current.off('receive_message');
        socketRef.current.off('message_delivered');
        socketRef.current.off('messages_read');
        socketRef.current.off('user_typing');
        socketRef.current.off('user_online');
        socketRef.current.off('user_offline');
        socketRef.current.off('room_joined');
        socketRef.current.off('connection_confirmed');
        socketRef.current.off('heartbeat_ack');
        socketRef.current.off('error');
        
        roomJoinedRef.current = false;
      }

      // Clear heartbeat
      if (heartbeatInterval.current) {
        clearInterval(heartbeatInterval.current);
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
          user_id: parseInt(userId),
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
        user_id: parseInt(userId),
        online: false,
        type: 'direct'
      });
    }
  };

  const setupSocket = () => {
    socketRef.current = initSocket();
    socketRef.current.auth = { token: user.id };
    
    // Clear processed message IDs and reset room state
    processedMessageIds.current.clear();
    roomJoinedRef.current = false;
    
    // Ensure socket is connected
    if (!socketRef.current.connected) {
      console.log('🔌 Connecting socket...');
      socketRef.current.connect();
      
      socketRef.current.on('connect', () => {
        console.log('✅ Socket connected, joining room...');
        joinRoom();
        startHeartbeat();
      });
    } else {
      console.log('✅ Socket already connected, joining room...');
      joinRoom();
      startHeartbeat();
    }
    
    // ✅ ENHANCED: Connection confirmation
    socketRef.current.on('connection_confirmed', (data) => {
      console.log('🎯 Connection confirmed:', data);
    });

    // ✅ ENHANCED: Heartbeat acknowledgment
    socketRef.current.on('heartbeat_ack', (data) => {
      console.log('💓 Heartbeat acknowledged:', data.timestamp);
    });
    
    // Handle room join confirmation
    socketRef.current.on('room_joined', (data) => {
      console.log('🏠 Room joined successfully:', data);
      roomJoinedRef.current = true;
    });
    
    // Handle errors
    socketRef.current.on('error', (error) => {
      console.error('❌ Socket error:', error);
    });
    
    // ✅ ENHANCED: Handle incoming messages with better deduplication
    socketRef.current.on('receive_message', (data) => {
      console.log('📨 REAL-TIME MESSAGE RECEIVED:', data);
      
      // Prevent duplicates
      if (processedMessageIds.current.has(data.id)) {
        console.log('⚠️ Duplicate message, skipping:', data.id);
        return;
      }
      
      processedMessageIds.current.add(data.id);
      
      setMessages(prev => {
        const exists = prev.find(msg => msg.id === data.id);
        if (exists) {
          console.log('⚠️ Message already in state:', data.id);
          return prev;
        }
        console.log('✅ Adding NEW message to state:', data.id);
        return [...prev, data];
      });
      
      // Auto-mark as read if not from current user and we're in the room
      if (data.sender_id !== user.id && roomJoinedRef.current) {
        setTimeout(() => {
          markAsRead();
        }, 1000);
      }
    });

    // Handle message delivery status
    socketRef.current.on('message_delivered', (data) => {
      console.log('📋 Message delivered:', data);
      setMessages(prev => 
        prev.map(msg => 
          msg.id === data.message_id 
            ? { ...msg, status: 'delivered' }
            : msg
        )
      );
    });

    // ✅ CRITICAL FIX: Enhanced message read status - BLUE TICK
    socketRef.current.on('messages_read', (data) => {
      console.log('🔵 BLUE TICK EVENT RECEIVED:', data);
      
      if (isGroupChat) {
        // Group chat logic
        if (data.group_id) {
          setMessages(prev => 
            prev.map(msg => 
              msg.sender_id === user.id 
                ? { ...msg, status: 'read' }
                : msg
            )
          );
          console.log('🔵 Updated group message status to read');
        }
      } else {
        // ✅ DIRECT CHAT BLUE TICK - CRITICAL FIX
        console.log('🔵 Processing direct chat blue tick:', {
          dataSenderId: data.sender_id,
          currentUserId: user.id,
          dataType: data.type,
          dataReaderId: data.reader_id
        });
        
        // ✅ MULTIPLE CONDITIONS FOR BLUE TICK
        const shouldUpdateBlueTick = (
          data.sender_id === user.id || // Current user is sender
          data.type === 'blue_tick' || 
          data.type === 'direct_chat_read' ||
          data.type === 'messages_read'
        );
        
        if (shouldUpdateBlueTick) {
          console.log('🔵 ✅ Updating blue tick for current user messages');
          
          setMessages(prev => 
            prev.map(msg => {
              if (msg.sender_id === user.id) {
                console.log(`🔵 Updating message ${msg.id} to READ status`);
                return { ...msg, status: 'read' };
              }
              return msg;
            })
          );
          
          console.log('🔵 ✅ BLUE TICK UPDATED SUCCESSFULLY');
        } else {
          console.log('🔵 ❌ Event not for current user messages');
        }
      }
    });

    // ✅ ENHANCED: Handle typing indicators with better state management
    socketRef.current.on('user_typing', (data) => {
      console.log('⌨️ Typing event received:', data);
      
      // Only process if it's for this chat and not from current user
      const currentChatId = normalizedChatId.current;
      
      if ((data.chat_id === currentChatId || data.chat_id === chatId) && data.user_id !== user.id) {
        console.log('⌨️ Processing typing event for current chat');
        
        setIsTyping(data.is_typing);
        
        setTypingUsers(prev => {
          const newSet = new Set(prev);
          if (data.is_typing) {
            newSet.add(data.user_id);
          } else {
            newSet.delete(data.user_id);
          }
          return newSet;
        });
        
        // Auto-clear typing indicator after 4 seconds
        if (data.is_typing) {
          setTimeout(() => {
            setIsTyping(false);
            setTypingUsers(prev => {
              const newSet = new Set(prev);
              newSet.delete(data.user_id);
              return newSet;
            });
          }, 4000);
        }
      }
    });

    // ✅ ENHANCED: Handle online status changes with immediate updates
    socketRef.current.on('user_online', (data) => {
      console.log('🟢 User online:', data);
      if (!isGroupChat && currentChat?.user_id === data.user_id) {
        setOnlineStatus(true);
        setCurrentChat(prev => prev ? { ...prev, online: true } : prev);
      }
    });

    socketRef.current.on('user_offline', (data) => {
      console.log('🔴 User offline:', data);
      if (!isGroupChat && currentChat?.user_id === data.user_id) {
        setOnlineStatus(false);
        setCurrentChat(prev => prev ? { ...prev, online: false } : prev);
      }
    });
  };

  // ✅ NEW: Heartbeat function for faster online status
  const startHeartbeat = () => {
    // Clear existing heartbeat
    if (heartbeatInterval.current) {
      clearInterval(heartbeatInterval.current);
    }

    // Send heartbeat every 30 seconds
    heartbeatInterval.current = setInterval(() => {
      if (socketRef.current && socketRef.current.connected) {
        socketRef.current.emit('heartbeat', { user_id: user.id, timestamp: Date.now() });
      }
    }, 30000);
  };

  const joinRoom = () => {
    if (socketRef.current && socketRef.current.connected && !roomJoinedRef.current) {
      const roomId = normalizedChatId.current || chatId;
      console.log(`🏠 Joining room: ${roomId}`);
      socketRef.current.emit('join', { chat_id: roomId });
    }
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
        console.log(`📚 Loaded ${response.data.length} messages`);
        setMessages(response.data);
        
        // Track processed messages
        response.data.forEach(msg => {
          processedMessageIds.current.add(msg.id);
        });
        
        // Mark as read after loading
        setTimeout(() => {
          markAsRead();
        }, 1000);
      }
    } catch (error) {
      console.error('Failed to load messages:', error);
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = () => {
    if (!roomJoinedRef.current) {
      console.log('⚠️ Cannot mark as read: room not joined yet');
      return;
    }
    
    try {
      if (isGroupChat) {
        markGroupMessagesAsRead();
      } else {
        const userIds = chatId.split('_');
        const otherUserId = parseInt(userIds.find(id => id !== user.id.toString()));
        markDirectMessagesAsRead(otherUserId);
      }
    } catch (error) {
      console.error('Error marking messages as read:', error);
    }
  };

  // ✅ ENHANCED: Direct message read with better event emission
  const markDirectMessagesAsRead = async (senderId) => {
    try {
      console.log(`🔵 MARK READ: Marking messages from ${senderId} as read by ${user.id}`);
      
      // Call API to mark messages as read
      await api.markMessagesAsRead({
        sender_id: senderId,
        receiver_id: user.id,
        reader_id: user.id
      });

      // ✅ ENHANCED: Send socket event for blue tick with better data
      if (socketRef.current && socketRef.current.connected) {
        const markReadData = {
          sender_id: senderId,
          receiver_id: user.id,
          reader_id: user.id,
          chat_id: normalizedChatId.current || chatId,
          timestamp: Date.now()
        };
        
        socketRef.current.emit('mark_read', markReadData);
        console.log('🔵 MARK READ: Emitted mark_read event:', markReadData);
      }
    } catch (error) {
      console.error('❌ Failed to mark direct messages as read:', error);
    }
  };

  const markGroupMessagesAsRead = async () => {
    try {
      await api.markGroupMessagesAsRead(groupId, user.id);
      
      if (socketRef.current && socketRef.current.connected) {
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
    if (!content.trim() || !user || !socketRef.current || !socketRef.current.connected) {
      console.log('⚠️ Cannot send message: requirements not met');
      return;
    }

    if (!roomJoinedRef.current) {
      console.log('⚠️ Cannot send message: room not joined yet');
      return;
    }

    let messageData;
    
    if (isGroupChat) {
      messageData = {
        sender_id: user.id,
        content: content.trim(),
        group_id: parseInt(groupId),
        chat_id: normalizedChatId.current || chatId
      };
    } else {
      const chatParts = chatId.split('_');
      const receiverId = chatParts.find(id => id !== user.id.toString());
      
      messageData = {
        sender_id: user.id,
        receiver_id: parseInt(receiverId),
        content: content.trim(),
        chat_id: normalizedChatId.current || chatId
      };
    }

    console.log('📤 SENDING MESSAGE:', messageData);
    
    try {
      socketRef.current.emit('send_message', messageData);
    } catch (error) {
      console.error('❌ Failed to send message:', error);
    }
  };

  const handleTyping = (isTypingNow) => {
    console.log(`⌨️ Typing status: ${isTypingNow} for chat: ${chatId}`);
    if (socketRef.current && socketRef.current.connected && roomJoinedRef.current) {
      socketRef.current.emit('typing', {
        chat_id: normalizedChatId.current || chatId,
        user_id: user.id,
        is_typing: isTypingNow
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

  const getTypingIndicator = () => {
    if (!isTyping && typingUsers.size === 0) return null;
    
    if (isGroupChat) {
      const typingUsersList = Array.from(typingUsers);
      const typingNames = typingUsersList.map(userId => {
        const member = groupMembers.find(m => m.id === userId);
        return member ? member.name.split(' ')[0] : 'Someone';
      });
      
      if (typingNames.length === 1) {
        return `${typingNames[0]} is typing...`;
      } else if (typingNames.length === 2) {
        return `${typingNames[0]} and ${typingNames[1]} are typing...`;
      } else if (typingNames.length > 2) {
        return `${typingNames[0]} and ${typingNames.length - 1} others are typing...`;
      }
    } else {
      return isTyping ? 'Typing...' : null;
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
                <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 rounded-full border border-white dark:border-gray-800 animate-pulse"></div>
              )}
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {currentChat?.user || 'Chat'}
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {getTypingIndicator() || 
                 (isGroupChat ? `${currentChat?.member_count || 0} members` :
                 (onlineStatus ? '🟢 Online' : '🔴 Offline'))}
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
        {(isTyping || typingUsers.size > 0) && (
          <div className="flex justify-start">
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-2 rounded-2xl">
              <div className="flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {getTypingIndicator()}
                </span>
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