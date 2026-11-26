import React, { useState } from 'react';
import { User, Lock, ArrowRight, Boxes } from 'lucide-react';

export default function LoginPage({ onLoginSuccess, switchToSignup, showToast }) {
  const [employeeNumber, setEmployeeNumber] = useState('EMP-2026-001');
  const [password, setPassword] = useState('password1234');

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ employee_number: employeeNumber, password })
      });
      const data = await res.json();
      if (res.ok) {
        showToast(data.message);
        onLoginSuccess(data.user);
      } else {
        showToast(data.detail || '로그인 실패', 'error');
      }
    } catch (err) {
      showToast('백엔드 서버 연결 실패', 'error');
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        
        <div className="auth-form-panel">
          <div className="auth-tabs">
            <button type="button" className="auth-tab-btn active">사원 로그인</button>
            <button type="button" onClick={switchToSignup} className="auth-tab-btn">사원 계정 등록</button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">사원번호 (Employee Number)</label>
              <div className="input-wrapper">
                <User className="input-icon" />
                <input type="text" placeholder='사번을 입력하세요' onChange={(e) => setEmployeeNumber(e.target.value)} className="form-input with-icon" />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">비밀번호 (Password)</label>
              <div className="input-wrapper">
                <Lock className="input-icon" />
                <input type="password" placeholder='비밀번호를 입력하세요' onChange={(e) => setPassword(e.target.value)} className="form-input with-icon" />
              </div>
            </div>

            <button type="submit" className="btn-primary">
              <span>시스템 로그인</span>
              <ArrowRight size={16} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}