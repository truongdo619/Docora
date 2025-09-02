import React, { createContext, useEffect, useState } from 'react';

interface AuthContextProps {
  isAuthenticated: boolean;
  setAuthenticated: React.Dispatch<React.SetStateAction<boolean>>;
}

export const AuthContext = createContext<AuthContextProps>({
  isAuthenticated: false,
  setAuthenticated: () => {},
});

export const AuthProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  const [isAuthenticated, setAuthenticated] = useState<boolean>(false);

  // useEffect(() => {
  //   const token = localStorage.getItem('accessToken');
  //   setAuthenticated(!!token);
  // }, []);

  useEffect(() => {
    const accessToken = localStorage.getItem('accessToken');
    const refreshToken = localStorage.getItem('refreshToken');
    const username = localStorage.getItem('username');

    // Check if all required items exist
    if (accessToken && refreshToken && username) {
      setAuthenticated(true);
    } else {
      setAuthenticated(false);
    }
  }, []);
  
  return (
    <AuthContext.Provider value={{ isAuthenticated, setAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
};
