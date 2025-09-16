import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav style={{
      backgroundColor: '#1976d2',
      color: 'white',
      padding: '10px 20px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
    }}>
      <Link 
        to="/" 
        style={{ 
          color: 'white', 
          textDecoration: 'none', 
          fontSize: '20px', 
          fontWeight: 'bold' 
        }}
      >
        Empires Online
      </Link>

      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        {user ? (
          <>
            <Link 
              to="/lobby" 
              style={{ color: 'white', textDecoration: 'none' }}
            >
              Game Lobby
            </Link>
            <span>Welcome, {user.username}!</span>
            <button 
              onClick={handleLogout}
              style={{
                background: 'none',
                border: '1px solid white',
                color: 'white',
                padding: '5px 15px',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Logout
            </button>
          </>
        ) : (
          <div style={{ display: 'flex', gap: '15px' }}>
            <Link 
              to="/login" 
              style={{ color: 'white', textDecoration: 'none' }}
            >
              Login
            </Link>
            <Link 
              to="/register" 
              style={{ color: 'white', textDecoration: 'none' }}
            >
              Register
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;