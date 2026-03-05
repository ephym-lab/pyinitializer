from __future__ import annotations
from models.project_config import ProjectConfig

class ScriptService:
    """Service for generating setup scripts."""
    
    SHEBANG = "#!/usr/bin/env bash\nset -e\n\n"

    def __init__(self, config: ProjectConfig):
        self.config = config

    def generate(self) -> str:
        pm = self.config.package_manager
        py = self.config.python_version
        name = self.config.project_name
        deps = self.config.dependencies

        if pm == "pip":
            return self._pip_script(py, deps)
        elif pm == "uv":
            return self._uv_script(py, deps)
        elif pm == "conda":
            return self._conda_script(py, name, deps)
        else:
            raise ValueError(f"Unsupported package manager: {pm}")

    def _deps_str(self, deps: list[str]) -> str:
        return " ".join(deps) if deps else ""

    def _pip_script(self, py: str, deps: list[str]) -> str:
        lines = [
            self.SHEBANG,
            f"python{py} -m venv .venv",
            'source .venv/bin/activate',
            "pip install --upgrade pip",
        ]
        if deps:
            lines.append(f"pip install {self._deps_str(deps)}")
        lines.append('\necho "Setup complete. Activate your environment with:"')
        lines.append('echo "source .venv/bin/activate"')
        return "\n".join(lines) + "\n"

    def _uv_script(self, py: str, deps: list[str]) -> str:
        lines = [
            self.SHEBANG,
            "# Requires: pip install uv  (or: curl -LsSf https://astral.sh/uv/install.sh | sh)",
            f"uv venv --python {py} .venv",
            "source .venv/bin/activate",
        ]
        if deps:
            lines.append(f"uv pip install {self._deps_str(deps)}")
        lines.append('\necho "Setup complete. Activate your environment with:"')
        lines.append('echo "source .venv/bin/activate"')
        return "\n".join(lines) + "\n"

    def _conda_script(self, py: str, name: str, deps: list[str]) -> str:
        lines = [
            self.SHEBANG,
            "# Requires: Conda (Miniconda or Anaconda)",
            f"conda create -n {name} python={py} -y",
            f"conda activate {name}",
        ]
        if deps:
            lines.append(f"conda install -n {name} {self._deps_str(deps)} -y 2>/dev/null || pip install {self._deps_str(deps)}")
        lines.append('\necho "Setup complete. Activate your environment with:"')
        lines.append(f'echo "   conda activate {name}"')
        return "\n".join(lines) + "\n"
