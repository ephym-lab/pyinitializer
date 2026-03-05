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
from services.projectbuilder import ProjectBuilder
from services.script_service import ScriptService

logger = logging.getLogger(__name__)

class ZipService:
    """Service for generating project ZIP files."""
    
    DEFAULT_LIMIT_MB = 50

    def __init__(self, config: ProjectConfig):
        self.config = config

    def generate(self) -> Tuple[StreamingResponse, bool]:
        """Build the project ZIP and return (StreamingResponse, venv_excluded)."""
        file_tree = ProjectBuilder(self.config).build()
        limit = self._size_limit_bytes()
        venv_excluded = False

        with tempfile.TemporaryDirectory(prefix="pyinit_") as tmpdir:
            project_dir = Path(tmpdir) / self.config.project_name

            # --- Write scaffold files ---
            for rel_path, content in file_tree.items():
                target = project_dir / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

            # --- Create virtual environment ---
            venv_dir = project_dir / ".venv"
            venv_created = self._create_venv(project_dir)

            # --- Install dependencies ---
            if venv_created and self.config.dependencies:
                self._install_dependencies(project_dir)

            # --- Check venv size ---
            if venv_created and venv_dir.exists():
                venv_size = self._dir_size(venv_dir)
                if venv_size > limit:
                    venv_excluded = True
                    logger.info("venv size %d bytes exceeds limit %d — excluding", venv_size, limit)
            else:
                venv_excluded = True

            # --- If venv excluded, add setup.sh ---
            if venv_excluded:
                setup_sh = ScriptService(self.config).generate()
                (project_dir / "setup.sh").write_text(setup_sh, encoding="utf-8")

            # --- Build ZIP ---
            zip_bytes = self._build_zip_buffer(project_dir, venv_excluded)

        return self._create_response(zip_bytes), venv_excluded

    def _size_limit_bytes(self) -> int:
        try:
            mb = int(os.environ.get("MAX_VENV_SIZE_MB", self.DEFAULT_LIMIT_MB))
        except ValueError:
            mb = self.DEFAULT_LIMIT_MB
        return mb * 1024 * 1024

    def _dir_size(self, path: Path) -> int:
        total = 0
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    pass
        return total

    def _create_venv(self, project_dir: Path) -> bool:
        cmd = self._venv_create_cmd(project_dir)
        try:
            result = subprocess.run(cmd, cwd=str(project_dir), capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                logger.info("venv created at %s", project_dir / ".venv")
                return True
            logger.warning("venv creation failed: %s", result.stderr)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning("venv creation error: %s", exc)
        return False

    def _venv_create_cmd(self, project_dir: Path) -> list[str]:
        pm = self.config.package_manager
        py = self.config.python_version
        venv = str(project_dir / ".venv")
        if pm == "uv":
            return ["uv", "venv", "--python", py, venv]
        return [f"python{py}", "-m", "venv", venv]

    def _install_dependencies(self, project_dir: Path) -> None:
        cmd = self._install_cmd(project_dir)
        if not cmd:
            return
        try:
            result = subprocess.run(cmd, cwd=str(project_dir), capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                logger.warning("dep install failed: %s", result.stderr)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning("dep install error: %s", exc)

    def _install_cmd(self, project_dir: Path) -> list[str] | None:
        if not self.config.dependencies:
            return None
        pm = self.config.package_manager
        venv = project_dir / ".venv"
        if pm == "uv":
            return ["uv", "pip", "install", "--python", str(venv / "bin" / "python")] + self.config.dependencies
        return [str(venv / "bin" / "pip"), "install"] + self.config.dependencies

    def _build_zip_buffer(self, project_dir: Path, venv_excluded: bool) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(project_dir.rglob("*")):
                if file_path.is_file():
                    rel = file_path.relative_to(project_dir)
                    if venv_excluded and rel.parts and rel.parts[0] == ".venv":
                        continue
                    zf.write(file_path, arcname=str(Path(self.config.project_name) / rel))
        buf.seek(0)
        return buf.read()

    def _create_response(self, zip_bytes: bytes) -> StreamingResponse:
        filename = f"{self.config.project_name}.zip"
        return StreamingResponse(
            iter([zip_bytes]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(zip_bytes)),
            },
        )
