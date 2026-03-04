"""
Preview router.

POST /preview → returns the file tree as JSON for the UI preview panel.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from models.project_config import ProjectConfig
from services import project_builder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/preview", tags=["Preview"])


@router.post("", summary="Get the project file tree as JSON")
async def preview_project(config: ProjectConfig):
    """
    Returns the in-memory file tree for the given configuration as a
    structured JSON list of file nodes, suitable for rendering in the UI.

    Each node has:
    - `path`    — relative path within the project
    - `type`    — `"file"` or `"directory"`
    - `content` — file content string (omitted for directories)
    """
    try:
        file_tree = project_builder.build_project(config)

        # Also collect intermediate directories
        all_dirs: set[str] = set()
        for rel_path in file_tree:
            parts = rel_path.replace("\\", "/").split("/")
            for i in range(1, len(parts)):
                all_dirs.add("/".join(parts[:i]))

        nodes = []

        for directory in sorted(all_dirs):
            nodes.append({"path": directory, "type": "directory"})

        for rel_path, content in sorted(file_tree.items()):
            nodes.append({"path": rel_path, "type": "file", "content": content})

        return {
            "project_name": config.project_name,
            "files": nodes,
            "total_files": len(file_tree),
        }
    except Exception as exc:
        logger.exception("Preview generation failed")
        raise HTTPException(
            status_code=500, detail=f"Preview generation failed: {exc}"
        ) from exc
