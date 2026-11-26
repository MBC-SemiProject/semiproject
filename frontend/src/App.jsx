import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import LoginPage from './auth/LoginPage';
import SignupPage from './auth/SignupPage';
import './App.css';

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [authView, setAuthView] = useState('login');
  const [activeTab, setActiveTab] = useState('dashboard');
  const [toasts, setToasts] = useState([]);

  const showToast = (message, type = 'success') => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  };

  if (!currentUser) {
    return (
      <>
        <div className="toast-container">
          {toasts.map((t) => (
            <div key={t.id} className={`toast-item ${t.type}`}>{t.message}</div>
          ))}
        </div>
        {authView === 'login' ? (
          <LoginPage onLoginSuccess={setCurrentUser} switchToSignup={() => setAuthView('signup')} showToast={showToast} />
        ) : (
          <SignupPage switchToLogin={() => setAuthView('login')} showToast={showToast} />
        )}
      </>
    );
  }

  return (
    <div className="app-layout">
      <Sidebar currentUser={currentUser} onLogout={() => setCurrentUser(null)} activeTab={activeTab} setActiveTab={setActiveTab} />
      <div className="main-content">
        <header className="top-header">
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, textTransform: 'capitalize' }}>{activeTab} 모듈 뷰</h2>
          <span style={{ fontSize: '0.75rem', color: '#34d399', backgroundColor: 'rgba(16, 185, 129, 0.1)', padding: '0.25rem 0.75rem', borderRadius: '9999px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
            {currentUser.name} ({currentUser.department}) 접속중
          </span>
        </header>

        <main style={{ padding: '1.5rem', maxWidth: '1200px', width: '100%', margin: '0 auto' }}>
          {activeTab === 'dashboard' && <div>대시보드 컴포넌트 영역</div>}
          {activeTab === 'forecasting' && <div>AI 예측 및 시뮬레이터 컴포넌트 영역</div>}
          {activeTab === 'items' && <div>물품 및 입출고 관리 컴포넌트 영역</div>}
          {activeTab === 'financials' && <div>재무 및 매출 통계 컴포넌트 영역</div>}
        </main>
      </div>
    </div>
  );
}