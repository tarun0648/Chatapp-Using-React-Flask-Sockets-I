import React, { useState, useEffect } from 'react';
import { Search, UserPlus, X } from 'lucide-react';
import { api } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

const GroupMemberModal = ({ groupId, onClose, onMemberAdded }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [adding, setAdding] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    if (searchTerm.trim()) {
      searchUsers();
    } else {
      setSearchResults([]);
    }
  }, [searchTerm]);

  const searchUsers = async () => {
    setLoading(true);
    try {
      const response = await api.searchUsersForGroup(groupId, searchTerm);
      if (response.success) {
        setSearchResults(response.data);
      }
    } catch (error) {
      console.error('Failed to search users:', error);
    } finally {
      setLoading(false);
    }
  };

  const addMember = async (userId) => {
    setAdding(true);
    try {
      const response = await api.addGroupMember(groupId, userId);
      if (response.success) {
        onMemberAdded();
        onClose();
      } else {
        alert('Failed to add member. You might not have permission.');
      }
    } catch (error) {
      console.error('Failed to add member:', error);
      alert('Failed to add member. Please try again.');
    } finally {
      setAdding(false);
    }
  };

  const getUserAvatar = (user) => {
    if (user.profile_picture) {
      const imageSrc = user.profile_picture.startsWith('http') 
        ? user.profile_picture 
        : `http://localhost:5000${user.profile_picture}`;
      
      return (
        <img 
          src={imageSrc}
          alt={user.name}
          className="w-10 h-10 rounded-full object-cover"
        />
      );
    }
    
    return (
      <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
        <span className="text-white font-semibold">
          {user.name.charAt(0).toUpperCase()}
        </span>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-md p-6 max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Add Member</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
          >
            <X size={20} />
          </button>
        </div>

        {/* Search Input */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="text"
            placeholder="Search users..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          />
        </div>

        {/* Search Results */}
        <div className="space-y-3">
          {loading ? (
            <div className="text-center py-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            </div>
          ) : searchResults.length > 0 ? (
            searchResults.map((searchUser) => (
              <div key={searchUser.id} className="flex items-center justify-between p-3 border border-gray-200 dark:border-gray-700 rounded-lg">
                <div className="flex items-center space-x-3">
                  {getUserAvatar(searchUser)}
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{searchUser.name}</p>
                    <p className="text-xs text-gray-600 dark:text-gray-400">@{searchUser.username}</p>
                  </div>
                </div>
                <button
                  onClick={() => addMember(searchUser.id)}
                  disabled={adding}
                  className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
                >
                  <UserPlus size={16} />
                </button>
              </div>
            ))
          ) : searchTerm.trim() ? (
            <p className="text-center text-gray-500 dark:text-gray-400 py-4">
              No users found
            </p>
          ) : (
            <p className="text-center text-gray-500 dark:text-gray-400 py-4">
              Search for users to add to the group
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default GroupMemberModal;