from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date
import db
from db import get_db
from passlib.context import CryptContext

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 1. 회원가입 요청 데이터 구조
class SignupRequest(BaseModel):
    employee_number: str
    email: str
    password: str
    name: str
    department: str
    phone: str
    gender: str
    role: str | None = "user"
    address: str | None = None
    birth_date: date | None = None

# 2. 로그인 요청 데이터 구조
class LoginRequest(BaseModel):
    employee_number: str
    password: str

# 3. 회원가입 엔드포인트
@router.post("/signup")
def signup(data: SignupRequest, session: Session = Depends(get_db)):
    
    hashed_password = pwd_context.hash(data.password)

    new_user = db.create_user(
        session,
        employee_number=data.employee_number,
        email=data.email,
        password=hashed_password,
        name=data.name,
        department=data.department,
        phone=data.phone,
        gender=data.gender,
        role=data.role,
        address=data.address,
        birth_date=data.birth_date
    )
    
    return {
        "status": "success",
        "message": f"'{new_user.name}'님 회원가입이 완료되었습니다!",
        "user_id": new_user.user_id
    }

# 4. 로그인 엔드포인트
@router.post("/login")
def login(data: LoginRequest, session: Session = Depends(get_db)):
    user = db.get_employee_number(session, data.employee_number)
    
    if not user or not pwd_context.verify(data.password, user.password):
        raise HTTPException(status_code=401, detail="사번 또는 비밀번호가 올바르지 않습니다.")
    
    return {
        "status": "success",
        "message": "로그인 성공!",
        "user": {
            "user_id": user.user_id,
            "employee_number": user.employee_number,
            "email": user.email,
            "name": user.name,
            "department": user.department,
            "role": user.role
        }
    }