from __future__ import annotations
import textwrap
from .base import ProjectBuilderBase, FileTree

class FastApiBuilder(ProjectBuilderBase):
    """FastAPI project scavenger."""

    def build(self, tree: FileTree) -> None:
        n = self.config.project_name

        # Entry point
        tree["app/main.py"] = textwrap.dedent(f"""\
            from fastapi import FastAPI
            from app.core.config import settings
            from app.api.router import api_router

            app = FastAPI(title=settings.PROJECT_NAME, version="0.1.0")

            app.include_router(api_router, prefix="/api/v1")


            @app.get("/health", tags=["Health"])
            def health():
                return {{"status": "ok", "project": settings.PROJECT_NAME}}
        """)

        # core/
        tree["app/core/config.py"] = textwrap.dedent(f"""\
            from pydantic_settings import BaseSettings


            class Settings(BaseSettings):
                PROJECT_NAME: str = "{n}"
                DATABASE_URL: str = "sqlite:///./app.db"
                SECRET_KEY: str = "changeme-in-production"

                class Config:
                    env_file = ".env"


            settings = Settings()
        """)

        tree["app/core/security.py"] = textwrap.dedent("""\
            # security.py — add JWT, password hashing, OAuth2 helpers here
            from passlib.context import CryptContext

            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


            def hash_password(password: str) -> str:
                return pwd_context.hash(password)


            def verify_password(plain: str, hashed: str) -> bool:
                return pwd_context.verify(plain, hashed)
        """)

        # db/
        tree["app/db/base.py"] = textwrap.dedent("""\
            from sqlalchemy import create_engine
            from sqlalchemy.orm import DeclarativeBase

            from app.core.config import settings

            engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})


            class Base(DeclarativeBase):
                pass
        """)

        tree["app/db/session.py"] = textwrap.dedent("""\
            from sqlalchemy.orm import sessionmaker
            from app.db.base import engine

            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


            def get_db():
                db = SessionLocal()
                try:
                    yield db
                finally:
                    db.close()
        """)

        tree["app/db/migrations/.gitkeep"] = ""

        # models/
        tree["app/models/user.py"] = textwrap.dedent("""\
            from sqlalchemy import Column, Integer, String
            from app.db.base import Base


            class User(Base):
                __tablename__ = "users"

                id = Column(Integer, primary_key=True, index=True)
                name = Column(String, nullable=False)
                email = Column(String, unique=True, index=True, nullable=False)
        """)

        # schemas/
        tree["app/schemas/user.py"] = textwrap.dedent("""\
            from pydantic import BaseModel, EmailStr


            class UserBase(BaseModel):
                name: str
                email: EmailStr


            class UserCreate(UserBase):
                pass


            class UserRead(UserBase):
                id: int

                model_config = {"from_attributes": True}
        """)

        # repositories/
        tree["app/repositories/user_repository.py"] = textwrap.dedent("""\
            from sqlalchemy.orm import Session
            from app.models.user import User
            from app.schemas.user import UserCreate


            def get_all(db: Session) -> list[User]:
                return db.query(User).all()


            def get_by_id(db: Session, user_id: int) -> User | None:
                return db.query(User).filter(User.id == user_id).first()


            def create(db: Session, data: UserCreate) -> User:
                user = User(**data.model_dump())
                db.add(user)
                db.commit()
                db.refresh(user)
                return user
        """)

        # services/
        tree["app/services/user_service.py"] = textwrap.dedent("""\
            from sqlalchemy.orm import Session
            from app.repositories import user_repository
            from app.schemas.user import UserCreate, UserRead


            def list_users(db: Session) -> list[UserRead]:
                return user_repository.get_all(db)


            def create_user(db: Session, data: UserCreate) -> UserRead:
                return user_repository.create(db, data)
        """)

        # api/
        tree["app/api/deps.py"] = textwrap.dedent("""\
            from typing import Generator
            from fastapi import Depends
            from sqlalchemy.orm import Session
            from app.db.session import get_db


            def get_session() -> Generator[Session, None, None]:
                yield from get_db()
        """)

        tree["app/api/routes/user_routes.py"] = textwrap.dedent("""\
            from fastapi import APIRouter, Depends
            from sqlalchemy.orm import Session
            from app.api.deps import get_session
            from app.schemas.user import UserCreate, UserRead
            from app.services import user_service

            router = APIRouter()


            @router.get("/", response_model=list[UserRead])
            def list_users(db: Session = Depends(get_session)):
                return user_service.list_users(db)


            @router.post("/", response_model=UserRead, status_code=201)
            def create_user(data: UserCreate, db: Session = Depends(get_session)):
                return user_service.create_user(db, data)
        """)

        tree["app/api/router.py"] = textwrap.dedent("""\
            from fastapi import APIRouter
            from app.api.routes import user_routes

            api_router = APIRouter()
            api_router.include_router(user_routes.router, prefix="/users", tags=["Users"])
        """)

        # utils/
        tree["app/utils/__init__.py"] = "# Add shared utility functions here\n"

        # tests/
        tree["tests/test_users.py"] = textwrap.dedent("""\
            from fastapi.testclient import TestClient
            from app.main import app

            client = TestClient(app)


            def test_health():
                response = client.get("/health")
                assert response.status_code == 200
                assert response.json()["status"] == "ok"


            def test_list_users_empty():
                response = client.get("/api/v1/users/")
                assert response.status_code == 200
        """)

        # Top-level files
        tree[".env"] = textwrap.dedent(f"""\
            PROJECT_NAME={n}
            DATABASE_URL=sqlite:///./app.db
            SECRET_KEY=changeme-in-production
        """)

        tree["Dockerfile"] = self._fastapi_dockerfile()

    def _fastapi_dockerfile(self) -> str:
        return textwrap.dedent(f"""\
            FROM python:{self.config.python_version}-slim

            WORKDIR /app

            COPY requirements.txt .
            RUN pip install --no-cache-dir -r requirements.txt

            COPY . .

            EXPOSE 8000

            CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
        """)
