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


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_project(config: ProjectConfig) -> FileTree:
    """Return a dict of {relative_path: content} for the scaffolded project."""
    tree: FileTree = {}

    _add_common_files(tree, config)
    _add_project_type_files(tree, config)

    return tree


# ---------------------------------------------------------------------------
# Common files (every project type)
# ---------------------------------------------------------------------------

def _add_common_files(tree: FileTree, config: ProjectConfig) -> None:
    tree[".gitignore"] = _gitignore()
    tree[".python-version"] = config.python_version + "\n"
    tree["README.md"] = _readme(config)

    # pyproject.toml or requirements.txt depending on package manager
    if config.package_manager in ("pip", "conda"):
        tree["requirements.txt"] = _requirements_txt(config)
    else:
        tree["pyproject.toml"] = _pyproject_toml(config)


# ---------------------------------------------------------------------------
# Project-type-specific files
# ---------------------------------------------------------------------------

def _add_project_type_files(tree: FileTree, config: ProjectConfig) -> None:
    pt = config.project_type
    if pt == "web-api":
        _add_web_api_files(tree, config)
    elif pt == "cli":
        _add_cli_files(tree, config)
    elif pt == "library":
        _add_library_files(tree, config)
    elif pt in ("data-science", "ml"):
        _add_datasci_files(tree, config)


# ---- web-api ----------------------------------------------------------------

def _add_web_api_files(tree: FileTree, config: ProjectConfig) -> None:
    fw = config.framework or "fastapi"
    tree["main.py"] = _web_api_main(fw, config)
    tree["tests/test_main.py"] = _web_api_test(fw, config)


def _web_api_main(framework: str, config: ProjectConfig) -> str:
    if framework == "fastapi":
        return dedent(f"""\
            from fastapi import FastAPI

            app = FastAPI(title="{config.project_name}", version="0.1.0")


            @app.get("/health")
            def health_check():
                return {{"status": "ok", "project": "{config.project_name}"}}


            @app.get("/")
            def root():
                return {{"message": "Welcome to {config.project_name}!"}}
        """)

    elif framework == "flask":
        return dedent(f"""\
            from flask import Flask, jsonify

            app = Flask(__name__)


            @app.route("/")
            def index():
                return jsonify(message="Welcome to {config.project_name}!")


            @app.route("/health")
            def health():
                return jsonify(status="ok", project="{config.project_name}")


            if __name__ == "__main__":
                app.run(debug=True)
        """)

    elif framework == "django":
        return dedent(f"""\
            # Django project — run the following to initialise:
            #
            #   django-admin startproject {config.module_name} .
            #   python manage.py migrate
            #   python manage.py runserver
            #
            # This file is a placeholder.  Django projects are created via
            # django-admin, which generates the full project layout for you.
            print("Run: django-admin startproject {config.module_name} .")
        """)

    elif framework == "litestar":
        return dedent(f"""\
            from litestar import Litestar, get


            @get("/")
            async def index() -> dict:
                return {{"message": "Welcome to {config.project_name}!"}}


            @get("/health")
            async def health() -> dict:
                return {{"status": "ok", "project": "{config.project_name}"}}


            app = Litestar([index, health])
        """)

    return "# main.py\n"


def _web_api_test(framework: str, _config: ProjectConfig) -> str:
    if framework == "fastapi":
        return dedent("""\
            from fastapi.testclient import TestClient
            from main import app

            client = TestClient(app)


            def test_health():
                response = client.get("/health")
                assert response.status_code == 200
                assert response.json()["status"] == "ok"


            def test_root():
                response = client.get("/")
                assert response.status_code == 200
        """)

    return dedent("""\
        # Add your tests here
        def test_placeholder():
            assert True
    """)


# ---- cli --------------------------------------------------------------------

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


# ---- library ----------------------------------------------------------------

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


# ---- data-science / ml ------------------------------------------------------

def _add_datasci_files(tree: FileTree, config: ProjectConfig) -> None:
    mn = config.module_name
    is_ml = config.project_type == "ml"

    tree[f"src/{mn}/__init__.py"] = f'"""{ config.project_name } package."""\n'
    tree["notebooks/.gitkeep"] = ""
    tree["data/.gitkeep"] = ""

    if is_ml:
        tree["main.py"] = dedent(f"""\
            \"\"\"
            {config.project_name} — ML project entry point.
            \"\"\"
            # Common ML imports — install via: pip install numpy pandas scikit-learn
            try:
                import numpy as np
                import pandas as pd
                from sklearn.model_selection import train_test_split

                print("Libraries loaded successfully!")
                print(f"NumPy version: {{np.__version__}}")
                print(f"Pandas version: {{pd.__version__}}")
            except ImportError as e:
                print(f"Missing dependency: {{e}}. Run your setup script first.")
        """)
    else:
        tree["main.py"] = dedent(f"""\
            \"\"\"
            {config.project_name} — data science entry point.
            \"\"\"
            # Common data-science imports — install via: pip install numpy pandas matplotlib
            try:
                import numpy as np
                import pandas as pd
                import matplotlib.pyplot as plt

                print("Libraries loaded successfully!")
                print(f"NumPy version: {{np.__version__}}")
                print(f"Pandas version: {{pd.__version__}}")
            except ImportError as e:
                print(f"Missing dependency: {{e}}. Run your setup script first.")
        """)


# ---------------------------------------------------------------------------
# Shared file templates
# ---------------------------------------------------------------------------

def _readme(config: ProjectConfig) -> str:
    setup_cmd = {
        "pip": "pip install -r requirements.txt",
        "uv": "uv pip install -r requirements.txt",
        "poetry": "poetry install",
        "pipenv": "pipenv install",
        "conda": f"conda env create -f environment.yml && conda activate {config.project_name}",
    }.get(config.package_manager, "pip install -r requirements.txt")

    venv_cmd = {
        "pip": f"python{config.python_version} -m venv .venv && source .venv/bin/activate",
        "uv": f"uv venv --python {config.python_version} .venv && source .venv/bin/activate",
        "poetry": f"poetry env use python{config.python_version}",
        "pipenv": f"pipenv --python {config.python_version}",
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
    mn = config.module_name
    deps = list(config.dependencies)
    if config.project_type == "web-api" and config.framework:
        if config.framework not in [d.lower() for d in deps]:
            deps.insert(0, config.framework)

    deps_toml = "\n".join(f'    "{d}",' for d in deps)
    python_requires = f">={config.python_version}"

    build_system = {
        "poetry": dedent("""\
            [build-system]
            requires = ["poetry-core>=1.0.0"]
            build-backend = "poetry.core.masonry.api"
        """),
        "uv": dedent("""\
            [build-system]
            requires = ["hatchling"]
            build-backend = "hatchling.build"
        """),
        "pipenv": dedent("""\
            [build-system]
            requires = ["setuptools>=68", "wheel"]
            build-backend = "setuptools.backends.legacy:build"
        """),
    }.get(config.package_manager, "")

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
