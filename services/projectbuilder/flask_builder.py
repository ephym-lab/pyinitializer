from __future__ import annotations
import textwrap
from .base import ProjectBuilderBase, FileTree

class FlaskBuilder(ProjectBuilderBase):
    """Flask project scavenger."""

    def build(self, tree: FileTree) -> None:
        n = self.config.project_name

        # Entry point (application factory pattern)
        tree["app/main.py"] = textwrap.dedent(f"""\
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
        tree["app/core/config.py"] = textwrap.dedent(f"""\
            import os


            class Config:
                PROJECT_NAME: str = "{n}"
                SECRET_KEY: str = os.environ.get("SECRET_KEY", "changeme-in-production")
                DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./app.db")
                SQLALCHEMY_TRACK_MODIFICATIONS = False
        """)

        tree["app/core/security.py"] = textwrap.dedent("""\
            # security.py — add password hashing, token helpers here
            from werkzeug.security import generate_password_hash, check_password_hash


            def hash_password(password: str) -> str:
                return generate_password_hash(password)


            def verify_password(plain: str, hashed: str) -> bool:
                return check_password_hash(hashed, plain)
        """)

        # db/
        tree["app/db/base.py"] = textwrap.dedent("""\
            from flask_sqlalchemy import SQLAlchemy

            db = SQLAlchemy()
        """)

        tree["app/db/session.py"] = textwrap.dedent("""\
            from app.db.base import db


            def init_db(app):
                db.init_app(app)
                with app.app_context():
                    db.create_all()
        """)

        tree["app/db/migrations/.gitkeep"] = ""

        # models/
        tree["app/models/user.py"] = textwrap.dedent("""\
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
        tree["app/schemas/user.py"] = textwrap.dedent("""\
            from dataclasses import dataclass


            @dataclass
            class UserCreate:
                name: str
                email: str
        """)

        # repositories/
        tree["app/repositories/user_repository.py"] = textwrap.dedent("""\
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
        tree["app/services/user_service.py"] = textwrap.dedent("""\
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

        tree["app/api/routes/user_routes.py"] = textwrap.dedent("""\
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

        tree["app/api/router.py"] = textwrap.dedent("""\
            from app.api.routes.user_routes import bp as users_bp


            def register_routes(app):
                app.register_blueprint(users_bp, url_prefix="/api/v1/users")
        """)

        # utils/
        tree["app/utils/__init__.py"] = "# Add shared utility functions here\n"

        # tests/
        tree["tests/test_users.py"] = textwrap.dedent("""\
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
        tree[".env"] = textwrap.dedent(f"""\
            PROJECT_NAME={n}
            DATABASE_URL=sqlite:///./app.db
            SECRET_KEY=changeme-in-production
        """)

        tree["Dockerfile"] = self._flask_dockerfile()

    def _flask_dockerfile(self) -> str:
        return textwrap.dedent(f"""\
            FROM python:{self.config.python_version}-slim

            WORKDIR /app

            COPY requirements.txt .
            RUN pip install --no-cache-dir -r requirements.txt

            COPY . .

            EXPOSE 5000

            CMD ["python", "-m", "flask", "--app", "app.main:app", "run", "--host", "0.0.0.0", "--port", "5000"]
        """)
