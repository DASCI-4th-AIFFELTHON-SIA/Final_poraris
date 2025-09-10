// frontend/src/HomePage.js

import React from 'react';
import { Link } from 'react-router-dom';
import background from './background.png';
import './HomePage.css';

function HomePage() {
  return (
    <div className="homepage-container">
      <img src={background} alt="Background" className="background-image" />

      <header className="navbar">
        <div className="logo">ELEMENT SPACE</div>
        <nav className="nav-links">
          <Link to="/app" className="nav-link">Planets</Link>
          <Link to="/app" className="nav-link">Astronomy</Link>
          <Link to="/app" className="nav-link">Space</Link>
        </nav>
        {/* <div className="menu-icon">
          <div className="line"></div>
          <div className="line"></div>
          <div className="line"></div>
        </div> */}
      </header>
      <div className="main-content">
        <h1 className="title">NOLB</h1>
        <p className="subtitle">Polaris Project</p>
        <div className="line-bar"></div>
      </div>
      <footer className="footer">
        With SIA
      </footer>
    </div>
  );
}

export default HomePage;