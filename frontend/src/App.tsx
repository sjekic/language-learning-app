import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './layouts/Layout';
import { AuthLayout } from './layouts/AuthLayout';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { StoryGeneratorPage } from './pages/StoryGeneratorPage';
import { StoryReaderPage } from './pages/StoryReaderPage';
import { StoryLibraryPage } from './pages/StoryLibraryPage';
import { VocabularyPage } from './pages/VocabularyPage';
import { useAuth } from './lib/AuthContext';

// Protected Route Component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { currentUser } = useAuth();
  
  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Auth Routes */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
        </Route>

        {/* App Routes - Protected */}
        <Route element={<Layout />}>
          <Route path="/generate" element={<ProtectedRoute><StoryGeneratorPage /></ProtectedRoute>} />
          <Route path="/library" element={<ProtectedRoute><StoryLibraryPage /></ProtectedRoute>} />
          <Route path="/read" element={<ProtectedRoute><StoryReaderPage /></ProtectedRoute>} />
          <Route path="/vocabulary" element={<ProtectedRoute><VocabularyPage /></ProtectedRoute>} />
        </Route>

        {/* Default Redirect */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
