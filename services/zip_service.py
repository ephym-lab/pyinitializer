"""
ZIP generation service.

Creates the project scaffold in a temp directory, sets up a virtual
environment, installs dependencies, checks the venv size against the
configurable limit, and returns a streaming ZIP response.
"""
from __future__ import annotations

import io
import logging
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Tuple

from fastapi.responses import StreamingResponse

from models.project_config import ProjectConfig
from services import project_builder, script_service

logger = logging.getLogger(__name__)

# Default size limit (bytes).  Overridden by MAX_VENV_SIZE_MB env var.
_DEFAULT_LIMIT_MB = 50


def _size_limit_bytes() -> int:
    try:
        mb = int(os.environ.get("MAX_VENV_SIZE_MB", _DEFAULT_LIMIT_MB))
    except ValueError:
        mb = _DEFAULT_LIMIT_MB
    return mb * 1024 * 1024


def _dir_size(path: Path) -> int:
    """Calculate total size of a directory tree in bytes."""
    total = 0
    for entry in path.rglob("*"):
        if entry.is_file():
            try:
                total += entry.stat().st_size
            except OSError:
                pass
    return total


# venv creation helpers

def _venv_create_cmd(config: ProjectConfig, project_dir: Path) -> list[str]:
    pm = config.package_manager
    py = config.python_version
    venv = str(project_dir / ".venv")

    if pm == "uv":
        return ["uv", "venv", "--python", py, venv]
    else:
        # pip and conda: use plain python venv
        return [f"python{py}", "-m", "venv", venv]


def _install_cmd(config: ProjectConfig, project_dir: Path) -> list[str] | None:
    if not config.dependencies:
        return None

    pm = config.package_manager
    venv = project_dir / ".venv"
    pip_bin = venv / "bin" / "pip"
    deps = config.dependencies

    if pm == "uv":
        return ["uv", "pip", "install", "--python", str(venv / "bin" / "python")] + deps
    else:
        return [str(pip_bin), "install"] + deps


# Public API

def generate_zip(config: ProjectConfig) -> Tuple[StreamingResponse, bool]:
    """
    Build the project ZIP in a temp directory and return (StreamingResponse, venv_excluded).

    The caller is responsible for setting the `X-Venv-Excluded` header based
    on the returned boolean.
    """
    file_tree = project_builder.build_project(config)
    limit = _size_limit_bytes()
    venv_excluded = False

    with tempfile.TemporaryDirectory(prefix="pyinit_") as tmpdir:
        project_dir = Path(tmpdir) / config.project_name

        # --- Write scaffold files ---
        for rel_path, content in file_tree.items():
            target = project_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        # --- Create virtual environment ---
        venv_dir = project_dir / ".venv"
        venv_created = False
        try:
            create_cmd = _venv_create_cmd(config, project_dir)
            result = subprocess.run(
                create_cmd,
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                venv_created = True
                logger.info("venv created at %s", venv_dir)
            else:
                logger.warning("venv creation failed: %s", result.stderr)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning("venv creation error: %s", exc)

        # --- Install dependencies ---
        if venv_created and config.dependencies:
            install_cmd = _install_cmd(config, project_dir)
            if install_cmd:
                try:
                    result = subprocess.run(
                        install_cmd,
                        cwd=str(project_dir),
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )
                    if result.returncode != 0:
                        logger.warning("dep install failed: %s", result.stderr)
                except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
                    logger.warning("dep install error: %s", exc)

        # --- Check venv size ---
        if venv_created and venv_dir.exists():
            venv_size = _dir_size(venv_dir)
            if venv_size > limit:
                venv_excluded = True
                logger.info(
                    "venv size %d bytes exceeds limit %d — excluding from ZIP",
                    venv_size,
                    limit,
                )
        else:
            venv_excluded = True  # wasn't created; auto-exclude

        # --- If venv excluded, add setup.sh ---
        if venv_excluded:
            setup_sh = script_service.generate_script(config)
            setup_path = project_dir / "setup.sh"
            setup_path.write_text(setup_sh, encoding="utf-8")

        # --- Build ZIP in memory ---
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(project_dir.rglob("*")):
                if file_path.is_file():
                    # Skip the venv if excluded
                    rel = file_path.relative_to(project_dir)
                    parts = rel.parts
                    if venv_excluded and parts and parts[0] == ".venv":
                        continue
                    zf.write(file_path, arcname=str(Path(config.project_name) / rel))

        buf.seek(0)
        zip_bytes = buf.read()

    # --- Return streaming response ---
    filename = f"{config.project_name}.zip"

    def _iter():
        yield zip_bytes

    response = StreamingResponse(
        _iter(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(zip_bytes)),
        },
    )
    return response, venv_excluded
