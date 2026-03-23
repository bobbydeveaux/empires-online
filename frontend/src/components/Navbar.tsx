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
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        Empires Online
      </Link>

      <div className="navbar-links">
        {user ? (
          <>
            <Link to="/lobby" className="navbar-link">
              Game Lobby
            </Link>
            <Link to="/stats" className="navbar-link">
              Stats
            </Link>
            <span>Welcome, {user.username}!</span>
            <button onClick={handleLogout} className="navbar-logout">
              Logout
            </button>
          </>
        ) : (
          <div className="navbar-auth-links">
            <Link to="/login" className="navbar-link">
              Login
            </Link>
            <Link to="/register" className="navbar-link">
              Register
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
