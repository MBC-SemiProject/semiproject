import React from 'react';
import { Boxes, LayoutDashboard, TrendingUp, PackagePlus, PieChart, LogOut } from 'lucide-react';

export default function Sidebar({ currentUser, onLogout, activeTab, setActiveTab }) {
  return (
    <aside className="sidebar">
      <div>
        <div className="sidebar-header">
          <div className="logo-box">
            <Boxes size={20} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>SemiProject</div>
            <div style={{ fontSize: '11px', color: '#34d399' }}>B2B Inventory AI</div>
          </div>
        </div>

        <nav className="nav-list">
          <p style={{ padding: '0 0.75rem', fontSize: '11px', color: '#64748b', fontWeight: 600, marginBottom: '0.25rem' }}>
            CORE MODULES
          </p>
          
          <button onClick={() => setActiveTab('dashboard')} className={`nav-btn ${activeTab === 'dashboard' ? 'active' : ''}`}>
            <LayoutDashboard size={16} /><span>대시보드</span>
          </button>

          <button onClick={() => setActiveTab('forecasting')} className={`nav-btn ${activeTab === 'forecasting' ? 'active' : ''}`}>
            <TrendingUp size={16} /><span>AI 예측 & 시뮬레이터</span>
          </button>

          <button onClick={() => setActiveTab('items')} className={`nav-btn ${activeTab === 'items' ? 'active' : ''}`}>
            <PackagePlus size={16} /><span>물품 및 입출고 관리</span>
          </button>

          <button onClick={() => setActiveTab('financials')} className={`nav-btn ${activeTab === 'financials' ? 'active' : ''}`}>
            <PieChart size={16} /><span>재무 및 매출 통계</span>
          </button>
        </nav>
      </div>

      <div className="sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem', padding: '0 0.5rem' }}>
          <div style={{ width: '2.25rem', height: '2.25rem', borderRadius: '50%', backgroundColor: '#059669', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '0.875rem' }}>
            {currentUser?.name?.charAt(0) || '원'}
          </div>
          <div>
            <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{currentUser?.name || '김원기'}</div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{currentUser?.department || '물류관리팀'} · {currentUser?.role || 'MANAGER'}</div>
          </div>
        </div>
        <button onClick={onLogout} className="btn-logout">
          <LogOut size={14} /><span>로그아웃</span>
        </button>
      </div>
    </aside>
  );
}