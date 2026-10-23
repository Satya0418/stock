import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { getAccessToken } from './tokenStore';

function RequireAuth({ children }) {
  const location = useLocation();
  const token = getAccessToken();
  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
}

export default RequireAuth;
