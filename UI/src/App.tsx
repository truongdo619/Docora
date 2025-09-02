import React, { useContext, useEffect } from 'react';
import { HashRouter as Router, Route, Routes, Navigate } from 'react-router-dom';

import { GlobalProvider } from './GlobalState';
import { AuthProvider, AuthContext } from './AuthContext';

import HomePage from './HomePage/HomePage';
import SignInPage from './SignInPage/SignInPage';
import ForgotPasswordPage from './SignInPage/ForgotPasswordPage';
import ResetPasswordPage from './SignInPage/ResetPasswordPage';
import SignUpPage from './SignUpPage/SignUpPage';
import ProfilePage from './ProfilePage/ProfilePage';
import ContactSupportPage from './ContactSupportPage/ContactSupportPage';
import DocumentListPage from './DocumentListPage/DocumentListPage';
import ResultComponent from './components/ResultComponent';
import DocsPage from './DocsPage/DocsPage';

// import setting from '../settings.json';
// import { injectDynamicCSS } from './injectStyles';

const ProtectedRoute = ({ children }: { children: JSX.Element }) => {
  const { isAuthenticated } = useContext(AuthContext);
  return isAuthenticated ? children : <Navigate to="/signin" />;
};

const App = () => {
  // useEffect(() => {
  //   injectDynamicCSS(setting);
  // }, []);

  return (
    <GlobalProvider>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/" element={<Navigate to="/home" />} />
            <Route path="/home" element={<HomePage />} />
            <Route path="/signin" element={<SignInPage />} />
            <Route path="/signup" element={<SignUpPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/support" element={<ContactSupportPage />} />

            <Route
              path="/documents"
              element={
                <ProtectedRoute>
                  <DocumentListPage />
                </ProtectedRoute>
              }
            />

            <Route
              path="/result"
              element={
                <ProtectedRoute>
                  <ResultComponent />
                </ProtectedRoute>
              }
            />

            {/* Redirect /docs routes */}
            <Route path="/docs" element={<Navigate to="/docs/v3.1/getting-started/overview" replace />} />
            <Route path="/docs/:version" element={<Navigate to="getting-started/overview" replace />} />
            <Route path="/docs/:version/:section" element={<Navigate to="overview" replace />} />
            <Route path="/docs/:version/:section/:page" element={<DocsPage />} />
          </Routes>
        </Router>
      </AuthProvider>
    </GlobalProvider>
  );
};

export default App;
