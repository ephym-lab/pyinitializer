"""
Project builder service.

Constructs an in-memory file tree (dict mapping relative path → file content)
for the given ProjectConfig.  No I/O is performed — callers write the files.
"""
from __future__ import annotations

from textwrap import dedent
from typing import Dict
from models.project_config import ProjectConfig


FileTree = Dict[str, str]


# Public entry point

def build_project(config: ProjectConfig) -> FileTree:
    """Return a dict of {relative_path: content} for the scaffolded project."""
    tree: FileTree = {}

    _add_common_files(tree, config)
    _add_project_type_files(tree, config)

    return tree


# Common files (every project type)

def _add_common_files(tree: FileTree, config: ProjectConfig) -> None:
    tree[".gitignore"] = _gitignore()
    tree[".python-version"] = config.python_version + "\n"
    tree["README.md"] = _readme(config)

    # uv uses pyproject.toml; pip and conda use requirements.txt
    if config.package_manager == "uv":
        tree["pyproject.toml"] = _pyproject_toml(config)
    else:
        tree["requirements.txt"] = _requirements_txt(config)


# Project-type-specific files

def _add_project_type_files(tree: FileTree, config: ProjectConfig) -> None:
    pt = config.project_type
    if pt == "web-api":
        _add_web_api_files(tree, config)
    elif pt == "cli":
        _add_cli_files(tree, config)
    elif pt == "library":
        _add_library_files(tree, config)
    elif pt == "ml":
        _add_datasci_files(tree, config)


# web-api

def _add_web_api_files(tree: FileTree, config: ProjectConfig) -> None:
    fw = config.framework or "fastapi"

    if fw == "fastapi":
        _scaffold_fastapi(tree, config)
    elif fw == "flask":
        _scaffold_flask(tree, config)
    elif fw == "django":
        # The actual Django project is created in zip_service.py via django-admin
        # we just add a hint file if the user looks at the scaffold without running startproject
        tree["README_DJANGO.md"] = dedent(f"""\
            # Django Project: {config.project_name}
            
            This project was automatically initialized using `django-admin startproject`.
            
            ## Apps Created:
            {chr(10).join(f"- {app}" for app in config.django_apps) if config.django_apps else "- No custom apps requested"}
            
            ## Next Steps:
            1. `python manage.py migrate`
            2. `python manage.py runserver`
        """)


# ── FastAPI ──────────────────────────────────────────────────────────────────

def _scaffold_fastapi(tree: FileTree, config: ProjectConfig) -> None:
    n = config.project_name

    # Entry point
    tree["app/main.py"] = dedent(f"""\
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
    tree["app/core/config.py"] = dedent(f"""\
        from pydantic_settings import BaseSettings


        class Settings(BaseSettings):
            PROJECT_NAME: str = "{n}"
            DATABASE_URL: str = "sqlite:///./app.db"
            SECRET_KEY: str = "changeme-in-production"

            class Config:
                env_file = ".env"


        settings = Settings()
    """)

    tree["app/core/security.py"] = dedent("""\
        # security.py — add JWT, password hashing, OAuth2 helpers here
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


        def hash_password(password: str) -> str:
            return pwd_context.hash(password)


        def verify_password(plain: str, hashed: str) -> bool:
            return pwd_context.verify(plain, hashed)
    """)

    # db/
    tree["app/db/base.py"] = dedent("""\
        from sqlalchemy import create_engine
        from sqlalchemy.orm import DeclarativeBase

        from app.core.config import settings

        engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})


        class Base(DeclarativeBase):
            pass
    """)

    tree["app/db/session.py"] = dedent("""\
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
    tree["app/models/user.py"] = dedent("""\
        from sqlalchemy import Column, Integer, String
        from app.db.base import Base


        class User(Base):
            __tablename__ = "users"

            id = Column(Integer, primary_key=True, index=True)
            name = Column(String, nullable=False)
            email = Column(String, unique=True, index=True, nullable=False)
    """)

    # schemas/
    tree["app/schemas/user.py"] = dedent("""\
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
    tree["app/repositories/user_repository.py"] = dedent("""\
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
    tree["app/services/user_service.py"] = dedent("""\
        from sqlalchemy.orm import Session
        from app.repositories import user_repository
        from app.schemas.user import UserCreate, UserRead


        def list_users(db: Session) -> list[UserRead]:
            return user_repository.get_all(db)


        def create_user(db: Session, data: UserCreate) -> UserRead:
            return user_repository.create(db, data)
    """)

    # api/
    tree["app/api/deps.py"] = dedent("""\
        from typing import Generator
        from fastapi import Depends
        from sqlalchemy.orm import Session
        from app.db.session import get_db


        def get_session() -> Generator[Session, None, None]:
            yield from get_db()
    """)

    tree["app/api/routes/user_routes.py"] = dedent("""\
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

    tree["app/api/router.py"] = dedent("""\
        from fastapi import APIRouter
        from app.api.routes import user_routes

        api_router = APIRouter()
        api_router.include_router(user_routes.router, prefix="/users", tags=["Users"])
    """)

    # utils/
    tree["app/utils/__init__.py"] = "# Add shared utility functions here\n"

    # tests/
    tree["tests/test_users.py"] = dedent("""\
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
    tree[".env"] = dedent(f"""\
        PROJECT_NAME={n}
        DATABASE_URL=sqlite:///./app.db
        SECRET_KEY=changeme-in-production
    """)

    tree["Dockerfile"] = _fastapi_dockerfile(config)


# ── Flask ─────────────────────────────────────────────────────────────────────

def _scaffold_flask(tree: FileTree, config: ProjectConfig) -> None:
    n = config.project_name
    mn = config.module_name

    # Entry point (application factory pattern)
    tree["app/main.py"] = dedent(f"""\
        from flask import Flask
        from app.core.config import Config
        from app.api.router import register_routes


        def create_app(config_class=Config) -> Flask:
            app = Flask(__name__)
            app.config.from_object(config_class)
            register_routes(app)

            @app.get("/health")
            def health():
                return {{"status": "ok", "project": app.config["PROJECT_NAME"]}}

            return app


        app = create_app()

        if __name__ == "__main__":
            app.run(debug=True)
    """)

    # core/
    tree["app/core/config.py"] = dedent(f"""\
        import os


        class Config:
            PROJECT_NAME: str = "{n}"
            SECRET_KEY: str = os.environ.get("SECRET_KEY", "changeme-in-production")
            DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./app.db")
            SQLALCHEMY_TRACK_MODIFICATIONS = False
    """)

    tree["app/core/security.py"] = dedent("""\
        # security.py — add password hashing, token helpers here
        from werkzeug.security import generate_password_hash, check_password_hash


        def hash_password(password: str) -> str:
            return generate_password_hash(password)


        def verify_password(plain: str, hashed: str) -> bool:
            return check_password_hash(hashed, plain)
    """)

    # db/
    tree["app/db/base.py"] = dedent("""\
        from flask_sqlalchemy import SQLAlchemy

        db = SQLAlchemy()
    """)

    tree["app/db/session.py"] = dedent("""\
        from app.db.base import db


        def init_db(app):
            db.init_app(app)
            with app.app_context():
                db.create_all()
    """)

    tree["app/db/migrations/.gitkeep"] = ""

    # models/
    tree["app/models/user.py"] = dedent("""\
        from app.db.base import db


        class User(db.Model):
            __tablename__ = "users"

            id = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.String(128), nullable=False)
            email = db.Column(db.String(256), unique=True, nullable=False)

            def to_dict(self):
                return {"id": self.id, "name": self.name, "email": self.email}
    """)

    # schemas/ (using marshmallow-style plain classes for simplicity)
    tree["app/schemas/user.py"] = dedent("""\
        from dataclasses import dataclass


        @dataclass
        class UserCreate:
            name: str
            email: str
    """)

    # repositories/
    tree["app/repositories/user_repository.py"] = dedent("""\
        from app.db.base import db
        from app.models.user import User


        def get_all() -> list[User]:
            return User.query.all()


        def get_by_id(user_id: int) -> User | None:
            return db.session.get(User, user_id)


        def create(name: str, email: str) -> User:
            user = User(name=name, email=email)
            db.session.add(user)
            db.session.commit()
            return user
    """)

    # services/
    tree["app/services/user_service.py"] = dedent("""\
        from app.repositories import user_repository
        from app.models.user import User


        def list_users() -> list[dict]:
            return [u.to_dict() for u in user_repository.get_all()]


        def create_user(name: str, email: str) -> dict:
            user = user_repository.create(name=name, email=email)
            return user.to_dict()
    """)

    # api/
    tree["app/api/deps.py"] = "# Add request-level dependencies / auth guards here\n"

    tree["app/api/routes/user_routes.py"] = dedent("""\
        from flask import Blueprint, jsonify, request
        from app.services import user_service

        bp = Blueprint("users", __name__)


        @bp.get("/")
        def list_users():
            return jsonify(user_service.list_users())


        @bp.post("/")
        def create_user():
            data = request.get_json()
            user = user_service.create_user(name=data["name"], email=data["email"])
            return jsonify(user), 201
    """)

    tree["app/api/router.py"] = dedent("""\
        from app.api.routes.user_routes import bp as users_bp


        def register_routes(app):
            app.register_blueprint(users_bp, url_prefix="/api/v1/users")
    """)

    # utils/
    tree["app/utils/__init__.py"] = "# Add shared utility functions here\n"

    # tests/
    tree["tests/test_users.py"] = dedent("""\
        import pytest
        from app.main import create_app


        @pytest.fixture
        def client():
            app = create_app()
            app.config["TESTING"] = True
            with app.test_client() as c:
                yield c


        def test_health(client):
            response = client.get("/health")
            assert response.status_code == 200
            assert response.get_json()["status"] == "ok"


        def test_list_users_empty(client):
            response = client.get("/api/v1/users/")
            assert response.status_code == 200
    """)

    # Top-level files
    tree[".env"] = dedent(f"""\
        PROJECT_NAME={n}
        DATABASE_URL=sqlite:///./app.db
        SECRET_KEY=changeme-in-production
    """)

    tree["Dockerfile"] = _flask_dockerfile(config)


# ── Django placeholder ────────────────────────────────────────────────────────

def _django_placeholder(config: ProjectConfig) -> str:
    return dedent(f"""\
        # Django project — run the following to initialise:
        #
        #   django-admin startproject {config.module_name} .
        #   python manage.py migrate
        #   python manage.py runserver
        #
        # This file is a placeholder. Django projects are created via
        # django-admin, which generates the full project layout for you.
        print("Run: django-admin startproject {config.module_name} .")
    """)


# ── Dockerfiles ───────────────────────────────────────────────────────────────

def _fastapi_dockerfile(config: ProjectConfig) -> str:
    return dedent(f"""\
        FROM python:{config.python_version}-slim

        WORKDIR /app

        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt

        COPY . .

        EXPOSE 8000

        CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    """)


def _flask_dockerfile(config: ProjectConfig) -> str:
    return dedent(f"""\
        FROM python:{config.python_version}-slim

        WORKDIR /app

        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt

        COPY . .

        EXPOSE 5000

        CMD ["python", "-m", "flask", "--app", "app.main:app", "run", "--host", "0.0.0.0", "--port", "5000"]
    """)




# cli

def _add_cli_files(tree: FileTree, config: ProjectConfig) -> None:
    deps_lower = [d.lower() for d in config.dependencies]
    use_typer = "typer" in deps_lower

    tree["main.py"] = _cli_main(use_typer, config)
    tree["tests/test_main.py"] = dedent("""\
        # CLI tests
        def test_placeholder():
            assert True
    """)


def _cli_main(use_typer: bool, config: ProjectConfig) -> str:
    if use_typer:
        return dedent(f"""\
            import typer

            app = typer.Typer()


            @app.command()
            def main(name: str = typer.Option("{config.project_name}", help="Your name")):
                \"\"\"Welcome to {config.project_name}!\"\"\"
                typer.echo(f"Hello, {{name}}!")


            if __name__ == "__main__":
                app()
        """)

    return dedent(f"""\
        import argparse


        def parse_args():
            parser = argparse.ArgumentParser(description="{config.project_name} CLI")
            parser.add_argument(
                "--name",
                default="{config.project_name}",
                help="Name to greet",
            )
            return parser.parse_args()


        def main():
            args = parse_args()
            print(f"Hello, {{args.name}}!")


        if __name__ == "__main__":
            main()
    """)


# library

def _add_library_files(tree: FileTree, config: ProjectConfig) -> None:
    mn = config.module_name
    tree[f"src/{mn}/__init__.py"] = dedent(f"""\
        \"\"\"
        {config.project_name} — a Python library.
        \"\"\"

        __version__ = "0.1.0"
        __all__: list[str] = []
    """)
    tree[f"tests/test_{mn}.py"] = dedent(f"""\
        import pytest
        from {mn} import __version__


        def test_version():
            assert __version__ == "0.1.0"
    """)
    tree["main.py"] = dedent(f"""\
        # Example usage of the {config.project_name} library
        from src.{mn} import __version__

        print(f"{config.project_name} v{{__version__}}")
    """)


# data-science / ml

def _add_datasci_files(tree: FileTree, config: ProjectConfig) -> None:
    mn = config.module_name

    tree[f"src/{mn}/__init__.py"] = f'"""{config.project_name} package."""\n'
    tree["notebooks/.gitkeep"] = ""
    tree["data/.gitkeep"] = ""

    tree["main.py"] = dedent(f"""\
        \"\"\"
        {config.project_name} — ML / data science entry point.
        \"\"\"
        # Common imports — install via your setup script or:
        #   pip install numpy pandas scikit-learn matplotlib
        try:
            import numpy as np
            import pandas as pd
            from sklearn.model_selection import train_test_split
            import matplotlib.pyplot as plt

            print("Libraries loaded successfully!")
            print(f"NumPy  : {{np.__version__}}")
            print(f"Pandas : {{pd.__version__}}")
        except ImportError as e:
            print(f"Missing dependency: {{e}}. Run your setup script first.")
    """)


# Shared file templates

def _readme(config: ProjectConfig) -> str:
    setup_cmd = {
        "pip": "pip install -r requirements.txt",
        "uv": "uv pip install -r requirements.txt",
        "conda": f"conda env create -f environment.yml && conda activate {config.project_name}",
    }.get(config.package_manager, "pip install -r requirements.txt")

    venv_cmd = {
        "pip": f"python{config.python_version} -m venv .venv && source .venv/bin/activate",
        "uv": f"uv venv --python {config.python_version} .venv && source .venv/bin/activate",
        "conda": f"conda create -n {config.project_name} python={config.python_version} -y && conda activate {config.project_name}",
    }.get(config.package_manager, "python -m venv .venv")

    deps_section = ""
    if config.dependencies:
        deps_list = "\n".join(f"- `{d}`" for d in config.dependencies)
        deps_section = f"\n## Dependencies\n\n{deps_list}\n"

    readme_lines = [
        f"# {config.project_name}",
        "",
        "> Generated by [Python Initializr](https://pystart.io)",
        "",
        f"**Python version:** {config.python_version}",
        f"**Package manager:** {config.package_manager}",
        f"**Project type:** {config.project_type}",
        "",
        "## Getting started",
        "",
        "### 1. Set up your virtual environment",
        "",
        "```bash",
        venv_cmd,
        "```",
        "",
        "### 2. Install dependencies",
        "",
        "```bash",
        setup_cmd,
        "```",
        "",
        "### 3. Run the project",
        "",
        "```bash",
        "python main.py",
        "```",
    ]
    if deps_section:
        readme_lines.append(deps_section)
    readme_lines += ["", "## License", "", "MIT", ""]
    return "\n".join(readme_lines)


def _requirements_txt(config: ProjectConfig) -> str:
    lines = list(config.dependencies)
    # Add framework dependency automatically for web-api projects
    if config.project_type == "web-api" and config.framework:
        if config.framework not in [d.lower() for d in lines]:
            lines.insert(0, config.framework)
    return "\n".join(lines) + "\n" if lines else "# Add your dependencies here\n"


def _pyproject_toml(config: ProjectConfig) -> str:
    """Only called for uv projects."""
    mn = config.module_name
    deps = list(config.dependencies)
    if config.project_type == "web-api" and config.framework:
        if config.framework not in [d.lower() for d in deps]:
            deps.insert(0, config.framework)

    deps_toml = "\n".join(f'    "{d}",' for d in deps)
    python_requires = f">={config.python_version}"

    build_system = dedent("""\
        [build-system]
        requires = ["hatchling"]
        build-backend = "hatchling.build"
    """)

    return dedent(f"""\
        [project]
        name = "{config.project_name}"
        version = "0.1.0"
        description = "A Python project generated by Python Initializr"
        readme = "README.md"
        requires-python = "{python_requires}"
        license = {{text = "MIT"}}
        dependencies = [
        {deps_toml}
        ]

        [project.scripts]
        {mn} = "{mn}:main"

        {build_system}
    """)


def _gitignore() -> str:
    return dedent("""\
        # Python
        __pycache__/
        *.py[cod]
        *$py.class
        *.so
        .Python
        build/
        develop-eggs/
        dist/
        downloads/
        eggs/
        .eggs/
        lib/
        lib64/
        parts/
        sdist/
        var/
        wheels/
        share/python-wheels/
        *.egg-info/
        .installed.cfg
        *.egg
        MANIFEST

        # Virtual environments
        .venv/
        venv/
        ENV/
        env/
        .env

        # Distribution / packaging
        *.whl

        # Unit test / coverage
        htmlcov/
        .tox/
        .nox/
        .coverage
        .coverage.*
        .cache
        nosetests.xml
        coverage.xml
        *.cover
        *.py,cover
        .hypothesis/
        .pytest_cache/
        cover/

        # Jupyter Notebooks
        .ipynb_checkpoints

        # pyenv
        .python-version

        # mypy
        .mypy_cache/
        .dmypy.json
        dmypy.json

        # IDEs
        .idea/
        .vscode/
        *.swp
        *.swo
        *~

        # OS
        .DS_Store
        Thumbs.db
    """)
