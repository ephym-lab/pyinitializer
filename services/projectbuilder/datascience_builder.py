from __future__ import annotations
import textwrap
from .base import ProjectBuilderBase, FileTree

class DataScienceBuilder(ProjectBuilderBase):
    """ML / Data Science project builder."""

    def build(self, tree: FileTree) -> None:
        n = self.config.project_name
        mn = self.config.module_name

        # data/
        tree["data/raw/.gitkeep"] = ""
        tree["data/processed/.gitkeep"] = ""

        # notebooks/
        tree["notebooks/.gitkeep"] = ""

        # src/
        tree[f"src/{mn}/__init__.py"] = ""
        
        # src/data/
        tree[f"src/{mn}/data/__init__.py"] = ""
        tree[f"src/{mn}/data/loading.py"] = textwrap.dedent("""\
            # Data loading & preprocessing
            def load_raw_data(path: str):
                return f"Loading data from {path}"
        """)

        # src/features/
        tree[f"src/{mn}/features/__init__.py"] = ""
        tree[f"src/{mn}/features/engineering.py"] = textwrap.dedent("""\
            # Feature engineering logic
            def extract_features(data):
                return data
        """)

        # src/models/
        tree[f"src/{mn}/models/__init__.py"] = ""
        tree[f"src/{mn}/models/train.py"] = textwrap.dedent("""\
            # Training, evaluation, inference
            def train_model(features, labels):
                return "Model trained"
        """)

        # src/utils/
        tree[f"src/{mn}/utils/__init__.py"] = ""
        tree[f"src/{mn}/utils/helpers.py"] = textwrap.dedent("""\
            # Helper utilities
            def logger_setup():
                pass
        """)

        # models/ (saved trained models)
        tree["models/.gitkeep"] = ""

        # configs/
        tree["configs/default.yaml"] = "# Default configuration settings\n"

        # tests/
        tree["tests/test_data.py"] = textwrap.dedent("""\
            def test_placeholder():
                assert True
        """)

        # Root files
        tree["main.py"] = textwrap.dedent(f"""\
            \"\"\"
            {n} — pipeline entry point.
            \"\"\"
            def main():
                print("Starting ML pipeline for {n}...")

            if __name__ == "__main__":
                main()
        """)
