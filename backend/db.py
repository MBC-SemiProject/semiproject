
from datetime import datetime

from sqlalchemy import String, Text, DateTime, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

engine = create_engine(
    "mysql+mysqlconnector://root:1234@localhost:3306/sample_db"
)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_number: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    birth_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True) 
    gender: Mapped[str] = mapped_column(String(1), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now()
    )

def get_db():
    with Session(engine) as session:
        yield session

def get_employee_number(session: Session, employee_number: str):
    stmt = select(User).where(User.employee_number == employee_number)
    return session.scalar(stmt)

def create_user(
    session: Session,
    employee_number: str,
    email: str,
    password: str,
    name: str,
    department: str,
    phone: str,
    gender: str,
    role: str | None = "user",
    address: str | None = None,
    birth_date = None
):
    user = User(
        employee_number=employee_number,
        email=email,
        password=password,
        name=name,
        department=department,
        phone=phone,
        gender=gender,
        role=role,
        address=address,
        birth_date=birth_date
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
