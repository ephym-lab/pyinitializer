from __future__ import annotations
import textwrap
from .base import ProjectBuilderBase, FileTree

class CliBuilder(ProjectBuilderBase):
    """CLI project scavenger."""

    def build(self, tree: FileTree) -> None:
        deps_lower = [d.lower() for d in self.config.dependencies]
        use_typer = "typer" in deps_lower

        tree["main.py"] = self._cli_main(use_typer)
        tree["tests/test_main.py"] = textwrap.dedent("""\
            # CLI tests
            def test_placeholder():
                assert True
        """)

    def _cli_main(self, use_typer: bool) -> str:
        config = self.config
        if use_typer:
            return textwrap.dedent(f"""\
                import typer

                app = typer.Typer()


                @app.command()
                def main(name: str = typer.Option("{config.project_name}", help="Your name")):
                    \"\"\"Welcome to {config.project_name}!\"\"\"
                    typer.echo(f"Hello, {{name}}!")


                if __name__ == "__main__":
                    app()
            """)

        return textwrap.dedent(f"""\
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

class LibraryBuilder(ProjectBuilderBase):
    """Library project scavenger."""

    def build(self, tree: FileTree) -> None:
        mn = self.config.module_name
        name = self.config.project_name
        tree[f"src/{mn}/__init__.py"] = textwrap.dedent(f"""\
            \"\"\"
            {name} — a Python library.
            \"\"\"

            __version__ = "0.1.0"
            __all__: list[str] = []
        """)
        tree[f"tests/test_{mn}.py"] = textwrap.dedent(f"""\
            import pytest
            from {mn} import __version__


            def test_version():
                assert __version__ == "0.1.0"
        """)
        tree["main.py"] = textwrap.dedent(f"""\
            # Example usage of the {name} library
            from src.{mn} import __version__

            print(f"{name} v{{__version__}}")
        """)

class DataScienceBuilder(ProjectBuilderBase):
    """ML / Data Science project scavenger."""

    def build(self, tree: FileTree) -> None:
        name = self.config.project_name
        mn = self.config.module_name

        tree[f"src/{mn}/__init__.py"] = f'"""{name} package."""\n'
        tree["notebooks/.gitkeep"] = ""
        tree["data/.gitkeep"] = ""

        tree["main.py"] = textwrap.dedent(f"""\
            \"\"\"
            {name} — ML / data science entry point.
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
