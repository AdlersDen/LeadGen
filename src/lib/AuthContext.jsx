import React, { createContext, useState, useContext } from 'react';

// Simple, no-auth context — authentication is handled externally.
const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  // No loading state needed — we are no longer calling a remote auth endpoint on mount.
  const [isLoadingAuth] = useState(false);
  const [isLoadingPublicSettings] = useState(false);
  const [authError] = useState(null);

  return (
    <AuthContext.Provider
      value={{
        user: null,
        isAuthenticated: true, // Internal tool — no login gate required
        isLoadingAuth,
        isLoadingPublicSettings,
        authError,
        navigateToLogin: () => {},
        logout: () => {},
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
