import React from 'react';
import { useNavigate } from 'react-router-dom';
import SignupForm from '../components/auth/SignupForm';

const SignupPage = () => {
  const navigate = useNavigate();

  return <SignupForm onSwitchToLogin={() => navigate('/')} />;
};

export default SignupPage;