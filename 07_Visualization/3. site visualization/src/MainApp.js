// frontend/src/MainApp.js

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import PlanetsTab from './PlanetsTab';
import './MainApp.css';

function MainApp() {
  const [activeTab, setActiveTab] = useState('planets');

  const renderContent = () => {
    switch (activeTab) {
      case 'planets':
        return <PlanetsTab />;
      case 'astronomy':
        return <div className="tab-content">Astronomy 탭 (준비 중)</div>;
      case 'space':
        return <div className="tab-content">Space 탭 (준비 중)</div>;
      default:
        return <PlanetsTab />;
    }
  };

  return (
    <div className="main-app">
      <nav className="main-navbar">
        <div className="nav-brand-container">
          <div className="logo-section">NOLB</div>
          <Link to="/" className="nav-brand">Project Polaris</Link>
        </div>
        <div className="nav-tabs">
          <button 
            className={`nav-tab ${activeTab === 'planets' ? 'active' : ''}`}
            onClick={() => setActiveTab('planets')}
          >
            Planets
          </button>
          <button 
            className={`nav-tab ${activeTab === 'astronomy' ? 'active' : ''}`}
            onClick={() => setActiveTab('astronomy')}
          >
            Astronomy
          </button>
          <button 
            className={`nav-tab ${activeTab === 'space' ? 'active' : ''}`}
            onClick={() => setActiveTab('space')}
          >
            Space
          </button>
        </div>
      </nav>
      
      <main className="main-app-content">
        {renderContent()}
      </main>
    </div>
  );
}

export default MainApp;