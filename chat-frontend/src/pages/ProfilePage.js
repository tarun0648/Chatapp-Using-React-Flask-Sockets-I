import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Moon, Sun, Edit2, Save, X, Camera } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { api } from '../services/api';
import Header from '../components/common/Header';

const ProfilePage = () => {
  const navigate = useNavigate();
  const { user, logout, updateUser } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [profileData, setProfileData] = useState({
    name: user?.name || '',
    email: user?.email || '',
    phone: user?.phone || '',
    profile_picture: user?.profile_picture || ''
  });

  const handleUpdateProfile = async () => {
    if (!user) return;
    
    setLoading(true);
    try {
      const response = await api.updateProfile(user.id, profileData);
      if (response.success) {
        updateUser(profileData);
        setIsEditing(false);
        alert('Profile updated successfully!');
      }
    } catch (error) {
      console.error('Failed to update profile:', error);
      alert('Failed to update profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setProfileData({
      name: user?.name || '',
      email: user?.email || '',
      phone: user?.phone || '',
      profile_picture: user?.profile_picture || ''
    });
    setIsEditing(false);
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setProfileData({
          ...profileData,
          profile_picture: e.target.result
        });
      };
      reader.readAsDataURL(file);
    }
  };

  const getProfileAvatar = () => {
    if (profileData.profile_picture) {
      return (
        <img 
          src={profileData.profile_picture} 
          alt={profileData.name}
          className="w-24 h-24 rounded-full object-cover"
        />
      );
    }
    
    return (
      <div className="w-24 h-24 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
        <span className="text-white text-2xl font-semibold">
          {profileData.name?.charAt(0).toUpperCase() || 'U'}
        </span>
      </div>
    );
  };

  const themeButton = (
    <button
      onClick={toggleTheme}
      className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
    >
      {isDark ? <Sun size={20} /> : <Moon size={20} />}
    </button>
  );

  return (
    <div className="h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
      <Header 
        title="Profile" 
        onBack={() => navigate('/chats')}
        actions={themeButton}
      />
      
      <div className="flex-1 p-6 overflow-y-auto">
        <div className="max-w-md mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <div className="text-center mb-6">
            <div className="relative inline-block">
              {getProfileAvatar()}
              {isEditing && (
                <label className="absolute -bottom-2 -right-2 w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center cursor-pointer hover:bg-blue-600 transition">
                  <Camera size={16} className="text-white" />
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageUpload}
                    className="hidden"
                  />
                </label>
              )}
            </div>
            
            {isEditing ? (
              <div className="mt-4 space-y-2">
                <input
                  type="text"
                  value={profileData.name}
                  onChange={(e) => setProfileData({...profileData, name: e.target.value})}
                  className="text-xl font-semibold text-center bg-transparent border-b-2 border-blue-500 text-gray-900 dark:text-gray-100 focus:outline-none"
                  placeholder="Your name"
                />
              </div>
            ) : (
              <div className="mt-4">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">{profileData.name}</h2>
                <p className="text-gray-600 dark:text-gray-400">@{user?.username}</p>
              </div>
            )}
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Email
              </label>
              {isEditing ? (
                <input
                  type="email"
                  value={profileData.email}
                  onChange={(e) => setProfileData({...profileData, email: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              ) : (
                <p className="text-sm text-gray-900 dark:text-gray-100 p-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  {profileData.email}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Phone
              </label>
              {isEditing ? (
                <input
                  type="tel"
                  value={profileData.phone}
                  onChange={(e) => setProfileData({...profileData, phone: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="Enter phone number"
                />
              ) : (
                <p className="text-sm text-gray-900 dark:text-gray-100 p-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  {profileData.phone || 'No phone number'}
                </p>
              )}
            </div>
            
            <div className="pt-4 space-y-3">
              <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Theme</span>
                <button
                  onClick={toggleTheme}
                  className="flex items-center space-x-2 px-3 py-1 bg-white dark:bg-gray-600 rounded-md border border-gray-300 dark:border-gray-500"
                >
                  {isDark ? <Sun size={16} className="text-yellow-500" /> : <Moon size={16} className="text-gray-600" />}
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    {isDark ? 'Light' : 'Dark'}
                  </span>
                </button>
              </div>

              {isEditing ? (
                <div className="flex space-x-3">
                  <button
                    onClick={handleCancel}
                    disabled={loading}
                    className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition disabled:opacity-50"
                  >
                    <X size={16} />
                    <span>Cancel</span>
                  </button>
                  <button
                    onClick={handleUpdateProfile}
                    disabled={loading}
                    className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:from-blue-600 hover:to-purple-700 transition disabled:opacity-50"
                  >
                    <Save size={16} />
                    <span>{loading ? 'Saving...' : 'Save'}</span>
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setIsEditing(true)}
                  className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:from-blue-600 hover:to-purple-700 transition"
                >
                  <Edit2 size={16} />
                  <span>Edit Profile</span>
                </button>
              )}
              
              <button
                onClick={handleLogout}
                className="w-full bg-red-600 dark:bg-red-700 text-white py-2 rounded-lg hover:bg-red-700 dark:hover:bg-red-800 transition"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;