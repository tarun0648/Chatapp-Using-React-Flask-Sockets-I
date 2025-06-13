// frontend/src/components/chat/MessageInput.js - ENHANCED VERSION
import React, { useState, useRef } from 'react';
import { Send } from 'lucide-react';

const MessageInput = ({ onSendMessage, onTyping }) => {
  const [message, setMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const typingTimeoutRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim()) {
      onSendMessage(message);
      setMessage('');
      handleTypingStop();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleChange = (e) => {
    setMessage(e.target.value);
    
    // Only trigger typing if there's actual content
    if (e.target.value.trim()) {
      handleTypingStart();
    } else {
      handleTypingStop();
    }
  };

  const handleTypingStart = () => {
    if (!isTyping) {
      console.log('Starting typing indicator');
      setIsTyping(true);
      onTyping?.(true);
    }
    
    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    
    // Set new timeout to stop typing after 1 second of inactivity
    typingTimeoutRef.current = setTimeout(() => {
      handleTypingStop();
    }, 1000);
  };

  const handleTypingStop = () => {
    if (isTyping) {
      console.log('Stopping typing indicator');
      setIsTyping(false);
      onTyping?.(false);
    }
    
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = null;
    }
  };

  // Handle focus lost
  const handleBlur = () => {
    setTimeout(() => {
      handleTypingStop();
    }, 100);
  };

  // Handle focus gained
  const handleFocus = () => {
    // Clear any existing timeouts when input is focused
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-6 py-4">
      <form onSubmit={handleSubmit} className="flex items-center space-x-3">
        <div className="flex-1">
          <input
            type="text"
            value={message}
            onChange={handleChange}
            onKeyPress={handleKeyPress}
            onBlur={handleBlur}
            onFocus={handleFocus}
            placeholder="Type a message..."
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            autoComplete="off"
          />
        </div>
        <button
          type="submit"
          disabled={!message.trim()}
          className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-2 rounded-lg hover:from-blue-600 hover:to-purple-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send size={20} />
        </button>
      </form>
    </div>
  );
};

export default MessageInput;