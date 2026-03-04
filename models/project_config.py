from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, validator


class ProjectConfig(BaseModel):
    project_name: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="Name of the project (used for directories and pyproject.toml)",
    )
    package_manager: Literal["pip", "uv", "conda"] = Field(
        ..., description="Package manager to use"
    )
    python_version: Literal["3.10", "3.11", "3.12", "3.13"] = Field(
        ..., description="Target Python version"
    )
    project_type: Literal["library", "cli", "web-api", "ml"] = Field(
        ..., description="Type of project to scaffold"
    )
    framework: Optional[Literal["fastapi", "flask", "django"]] = Field(
        default=None,
        description="Web framework (only relevant for project_type='web-api')",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Additional PyPI package names to install",
    )
    django_apps: List[str] = Field(
        default_factory=list,
        description="Django app names to create with manage.py startapp (only for framework='django')",
    )

    @validator("project_name")
    def sanitize_project_name(cls, v: str) -> str:
        import re
        # Allow letters, digits, hyphens, underscores only
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError(
                "project_name may only contain letters, digits, hyphens, and underscores"
            )
        return v

    @validator("framework", always=True)
    def framework_requires_web_api(
        cls, v: Optional[str], values: dict
    ) -> Optional[str]:
        project_type = values.get("project_type")
        if v is not None and project_type != "web-api":
            raise ValueError(
                "framework may only be set when project_type is 'web-api'"
            )
        return v

    @validator("django_apps", always=True)
    def django_apps_only_for_django(
        cls, v: List[str], values: dict
    ) -> List[str]:
        import re
        if v and values.get("framework") != "django":
            raise ValueError(
                "django_apps may only be set when framework is 'django'"
            )
        for app in v:
            if not re.match(r"^[a-z][a-z0-9_]*$", app):
                raise ValueError(
                    f"Django app name '{app}' must be lowercase letters, digits, and underscores, starting with a letter"
                )
        return v

    @property
    def module_name(self) -> str:
        """Importable Python module name derived from project_name."""
        return self.project_name.replace("-", "_").lower()
