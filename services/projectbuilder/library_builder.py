from __future__ import annotations
import textwrap
from .base import ProjectBuilderBase, FileTree

class LibraryBuilder(ProjectBuilderBase):
    """Library project builder."""

    def build(self, tree: FileTree) -> None:
        n = self.config.project_name
        mn = self.config.module_name

        # src/{mn}/
        tree[f"src/{mn}/__init__.py"] = textwrap.dedent(f"""\
            \"\"\"
            {n} — a professional Python library.
            \"\"\"
            __version__ = "0.1.0"
        """)

        # src/{mn}/core/
        tree[f"src/{mn}/core/__init__.py"] = ""
        tree[f"src/{mn}/core/main.py"] = textwrap.dedent(f"""\
            class {mn.capitalize()}Core:
                \"\"\"Core logic for {n}.\"\"\"
                
                def __init__(self):
                    self.initialized = True

                def run(self):
                    return "Library is running"
        """)

        # src/{mn}/utils/
        tree[f"src/{mn}/utils/__init__.py"] = ""
        tree[f"src/{mn}/utils/helpers.py"] = textwrap.dedent("""\
            def format_message(msg: str) -> str:
                return f"[Library] {msg}"
        """)

        # src/{mn}/exceptions.py
        tree[f"src/{mn}/exceptions.py"] = textwrap.dedent(f"""\
            class {mn.capitalize()}Error(Exception):
                \"\"\"Base exception for {n}.\"\"\"
                pass
        """)

        # tests/
        tree["tests/__init__.py"] = ""
        tree["tests/test_core.py"] = textwrap.dedent(f"""\
            from {mn}.core.main import {mn.capitalize()}Core

            def test_core_init():
                core = {mn.capitalize()}Core()
                assert core.initialized is True
        """)

        # docs/
        tree["docs/.gitkeep"] = ""

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
