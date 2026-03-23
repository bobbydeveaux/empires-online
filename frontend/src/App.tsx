import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './hooks/useAuth';
import Login from './pages/Login';
import Register from './pages/Register';
import GameLobby from './pages/GameLobby';
import Game from './pages/Game';
import SpectatorView from './pages/SpectatorView';
import StatsPage from './pages/PlayerStats';
import Navbar from './components/Navbar';
import { ToastProvider } from './components/Toast';
import './App.css';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <div className="loading">Loading...</div>;
  }
  
  if (!user) {
    return <Navigate to="/login" />;
  }
  
  return <>{children}</>;
};

const HomePage: React.FC = () => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <div className="loading">Loading...</div>;
  }
  
  if (user) {
    return <Navigate to="/lobby" replace />;
  }
  
  return <Navigate to="/login" replace />;
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <ToastProvider>
        <Router>
          <div className="App">
            <Navbar />
            <main className="main-content">
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/lobby" element={
                  <ProtectedRoute>
                    <GameLobby />
                  </ProtectedRoute>
                } />
                <Route path="/game/:gameId" element={
                  <ProtectedRoute>
                    <Game />
                  </ProtectedRoute>
                } />
                <Route path="/spectate/:gameId" element={
                  <ProtectedRoute>
                    <SpectatorView />
                  </ProtectedRoute>
                } />
                <Route path="/stats" element={
                  <ProtectedRoute>
                    <StatsPage />
                  </ProtectedRoute>
                } />
                <Route path="/stats/:playerId" element={
                  <ProtectedRoute>
                    <StatsPage />
                  </ProtectedRoute>
                } />
                <Route path="/" element={<HomePage />} />
              </Routes>
            </main>
          </div>
        </Router>
      </ToastProvider>
    </AuthProvider>
  );
};

export default App;