"""
Script generation service.

Produces a shell script (bash) that recreates the virtual environment and
installs all dependencies for a given ProjectConfig.  The output is adapted
to the chosen package manager.
"""
from __future__ import annotations

from models.project_config import ProjectConfig


_SHEBANG = "#!/usr/bin/env bash\nset -e\n\n"


def _deps_str(deps: list[str]) -> str:
    return " ".join(deps) if deps else ""


def generate_script(config: ProjectConfig) -> str:
    pm = config.package_manager
    py = config.python_version
    name = config.project_name
    deps = config.dependencies

    if pm == "pip":
        return _pip_script(py, deps)
    elif pm == "uv":
        return _uv_script(py, deps)
    elif pm == "conda":
        return _conda_script(py, name, deps)
    else:
        raise ValueError(f"Unsupported package manager: {pm}")


# Package-manager-specific generators

def _pip_script(py: str, deps: list[str]) -> str:
    lines = [
        _SHEBANG,
        f"python{py} -m venv .venv",
        'source .venv/bin/activate',
        "pip install --upgrade pip",
    ]
    if deps:
        lines.append(f"pip install {_deps_str(deps)}")
    lines.append('\necho "✅ Setup complete. Activate your environment with:"')
    lines.append('echo "   source .venv/bin/activate"')
    return "\n".join(lines) + "\n"


def _uv_script(py: str, deps: list[str]) -> str:
    lines = [
        _SHEBANG,
        "# Requires: pip install uv  (or: curl -LsSf https://astral.sh/uv/install.sh | sh)",
        f"uv venv --python {py} .venv",
        "source .venv/bin/activate",
    ]
    if deps:
        lines.append(f"uv pip install {_deps_str(deps)}")
    lines.append('\necho "✅ Setup complete. Activate your environment with:"')
    lines.append('echo "   source .venv/bin/activate"')
    return "\n".join(lines) + "\n"



def _conda_script(py: str, name: str, deps: list[str]) -> str:
    lines = [
        _SHEBANG,
        "# Requires: Conda (Miniconda or Anaconda)",
        f"conda create -n {name} python={py} -y",
        f"conda activate {name}",
    ]
    if deps:
        lines.append(f"conda install -n {name} {_deps_str(deps)} -y 2>/dev/null || pip install {_deps_str(deps)}")
    lines.append('\necho "✅ Setup complete. Activate your environment with:"')
    lines.append(f'echo "   conda activate {name}"')
    return "\n".join(lines) + "\n"
