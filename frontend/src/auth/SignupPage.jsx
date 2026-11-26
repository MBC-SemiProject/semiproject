import React, { useState } from 'react';

export default function SignupPage({ switchToLogin, showToast }) {
  const [formData, setFormData] = useState({
    employee_number: '', email: '', password: '', name: '',
    department: '물류관리팀', role: 'STAFF', phone: '',
    birth_date: '1996-05-15', gender: 'M', address: ''
  });

  const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('http://localhost:8000/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      const data = await res.json();
      if (res.ok) {
        showToast(data.message);
        switchToLogin();
      } else {
        showToast(data.detail || '회원가입 실패', 'error');
      }
    } catch (err) {
      showToast('백엔드 서버 연결 실패', 'error');
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-card" style={{ gridTemplateColumns: '1fr', maxWidth: '600px' }}>
        <div className="auth-form-panel">
          <div className="auth-tabs">
            <button type="button" onClick={switchToLogin} className="auth-tab-btn">사원 로그인</button>
            <button type="button" className="auth-tab-btn active">사원 계정 등록</button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-grid-2 form-group">
              <div>
                <label className="form-label">사원번호 (아이디) *</label>
                <input type="text" name="employee_number" required placeholder="EMP-2026-002" onChange={handleChange} className="form-input" />
              </div>
              <div>
                <label className="form-label">사원 이름 *</label>
                <input type="text" name="name" required placeholder="홍길동" onChange={handleChange} className="form-input" />
              </div>
            </div>

            <div className="form-grid-2 form-group">
              <div>
                <label className="form-label">이메일 *</label>
                <input type="email" name="email" required placeholder="gildong@semiproject.co.kr" onChange={handleChange} className="form-input" />
              </div>
              <div>
                <label className="form-label">비밀번호 *</label>
                <input type="password" name="password" required placeholder="••••••••" onChange={handleChange} className="form-input" />
              </div>
            </div>

            <div className="form-grid-2 form-group">
              <div>
                <label className="form-label">전화번호 *</label>
                <input type="tel" name="phone" required placeholder="010-1234-5678" onChange={handleChange} className="form-input" />
              </div>
              <div>
                <label className="form-label">주소 *</label>
                <input type="add" name="address" required placeholder="서울특별시 종로구" onChange={handleChange} className="form-input" />
              </div>
              <div className="form-group">
                <label className="form-label">생년월일 *</label>
                <input type="date" name="birth_date" required value={formData.birth_date} onChange={handleChange} className="form-input" />
              </div>
              <div>
                <label className="form-label">성별 *</label>
                <select name="gender" onChange={handleChange} className="form-input">
                  <option value="M">남자</option>
                  <option value="F">여자</option>
                </select>
              </div>

              <div>
                <label className="form-label">소속 부서 *</label>
                <select name="department" onChange={handleChange} className="form-input">
                  <option value="물류관리팀">물류관리팀</option>
                  <option value="수요예측AI팀">수요예측AI팀</option>
                  <option value="구매발주팀">구매발주팀</option>
                  <option value="재무기획팀">재무기획팀</option>
                </select>
              </div>
              <div>
                <label className="form-label">직위 *</label>
                <select name="role" onChange={handleChange} className="form-input">
                  <option value="사원">사원</option>
                  <option value="주임">주임</option>
                  <option value="대리">대리</option>
                  <option value="부장">부장</option>
                </select>
              </div>
            </div>

            <button type="submit" className="btn-primary">사원 등록 완료</button>
          </form>
        </div>
      </div>
    </div>
  );
}