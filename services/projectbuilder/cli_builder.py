from __future__ import annotations
import textwrap
from .base import ProjectBuilderBase, FileTree

class CliBuilder(ProjectBuilderBase):
    """CLI project builder."""

    def build(self, tree: FileTree) -> None:
        n = self.config.project_name
        mn = self.config.module_name

        # src/{mn}/__init__.py
        tree[f"src/{mn}/__init__.py"] = ""

        # src/{mn}/client.py
        tree[f"src/{mn}/client.py"] = textwrap.dedent(f"""\
            import logging
            from .config import Settings
            from .exceptions import APIClientError

            logger = logging.getLogger(__name__)

            class APIClient:
                \"\"\"Main client interface for {n}.\"\"\"
                
                def __init__(self, settings: Settings | None = None):
                    self.settings = settings or Settings()
                    logger.info("Initialized {n} client")

                def connect(self):
                    \"\"\"Placeholder for connection logic.\"\"\"
                    if not self.settings.base_url:
                        raise APIClientError("Base URL is required")
                    return True
        """)

        # src/{mn}/config.py
        tree[f"src/{mn}/config.py"] = textwrap.dedent(f"""\
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                \"\"\"Client configuration settings.\"\"\"
                base_url: str = "https://api.example.com"
                api_key: str = "your-api-key"
                timeout: int = 30

                class Config:
                    env_file = ".env"
        """)

        # src/{mn}/exceptions.py
        tree[f"src/{mn}/exceptions.py"] = textwrap.dedent(f"""\
            class {mn.capitalize()}Error(Exception):
                \"\"\"Base exception for {n}.\"\"\"
                pass

            class APIClientError({mn.capitalize()}Error):
                \"\"\"Raised when the API client encounters an error.\"\"\"
                pass
        """)

        # src/{mn}/services/
        tree[f"src/{mn}/services/__init__.py"] = ""
        tree[f"src/{mn}/services/users.py"] = textwrap.dedent("""\
            from ..client import APIClient

            class UserService:
                \"\"\"Service for user-related API endpoints.\"\"\"
                
                def __init__(self, client: APIClient):
                    self.client = client

                def get_current_user(self):
                    \"\"\"Fetch the currently authenticated user.\"\"\"
                    return {"id": 1, "username": "admin"}
        """)

        # src/{mn}/models/
        tree[f"src/{mn}/models/__init__.py"] = ""
        tree[f"src/{mn}/models/user.py"] = textwrap.dedent("""\
            from pydantic import BaseModel

            class User(BaseModel):
                \"\"\"User domain model.\"\"\"
                id: int
                username: str
        """)

        # src/{mn}/utils/
        tree[f"src/{mn}/utils/__init__.py"] = ""
        tree[f"src/{mn}/utils/http.py"] = textwrap.dedent("""\
            # HTTP helper utilities (serialization, auth headers, etc.)
            def get_auth_header(api_key: str) -> dict:
                return {"Authorization": f"Bearer {api_key}"}
        """)

        # tests/
        tree["tests/test_client.py"] = textwrap.dedent(f"""\
            import pytest
            from {mn}.client import APIClient

            def test_client_init():
                client = APIClient()
                assert client.settings.timeout == 30
        """)

        # examples/
        tree["examples/basic_usage.py"] = textwrap.dedent(f"""\
            from {mn}.client import APIClient

            def main():
                client = APIClient()
                print(f"Connecting to {{client.settings.base_url}}...")

            if __name__ == "__main__":
                main()
        """)

        # Top-level files
        tree["LICENSE"] = "MIT License"
        tree[".pre-commit-config.yaml"] = textwrap.dedent("""\
            repos:
              - repo: https://github.com/pre-commit/pre-commit-hooks
                rev: v4.4.0
                hooks:
                  - id: trailing-whitespace
                  - id: end-of-file-fixer
        """)
