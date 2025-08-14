import React, { useState } from 'react';
import LoginForm from '../components/auth/LoginForm';
import SignupForm from '../components/auth/SignupForm';

const LoginPage = () => {
  const [showSignup, setShowSignup] = useState(false);

  if (showSignup) {
    return <SignupForm onSwitchToLogin={() => setShowSignup(false)} />;
  }

  return <LoginForm onSwitchToSignup={() => setShowSignup(true)} />;
};

export default LoginPage;