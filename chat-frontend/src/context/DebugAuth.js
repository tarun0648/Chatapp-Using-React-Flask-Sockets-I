import React from 'react';
import { useAuth } from '../context/AuthContext';

const DebugAuth = () => {
  const { user, isAuthenticated, loading } = useAuth();

  return (
    <div className="fixed top-4 right-4 bg-black text-white p-2 rounded text-xs z-50">
      <div>Loading: {loading ? 'Yes' : 'No'}</div>
      <div>Authenticated: {isAuthenticated ? 'Yes' : 'No'}</div>
      <div>User: {user ? user.username : 'None'}</div>
      <div>Token: {localStorage.getItem('token') ? 'Exists' : 'None'}</div>
    </div>
  );
};

export default DebugAuth;