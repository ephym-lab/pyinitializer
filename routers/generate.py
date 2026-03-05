"""
Generate router.

POST /generate/zip    → returns a ZIP download
POST /generate/script → returns a shell script
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import PlainTextResponse

from models.project_config import ProjectConfig
from services import script_service, zip_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/zip", summary="Download project as a ZIP archive")
async def generate_zip(config: ProjectConfig, response: Response):
    """
    Scaffold the project, create a virtualenv, install dependencies,
    and return a ZIP file.

    If the venv exceeds the configured size limit (default 50 MB), the venv
    is excluded from the ZIP, a `setup.sh` script is included instead, and
    the response header `X-Venv-Excluded: true` is set.
    """
    try:
        streaming_response, venv_excluded = zip_service.ZipService(config).generate()
        if venv_excluded:
            streaming_response.headers["X-Venv-Excluded"] = "true"
        return streaming_response
    except Exception as exc:
        logger.exception("ZIP generation failed")
        raise HTTPException(status_code=500, detail=f"ZIP generation failed: {exc}") from exc


@router.post(
    "/script",
    response_class=PlainTextResponse,
    summary="Download setup shell script",
    responses={200: {"content": {"text/plain": {}}}},
)
async def generate_script(config: ProjectConfig):
    """
    Return a bash shell script that creates the virtualenv and installs
    dependencies for the given configuration.
    """
    try:
        script = script_service.ScriptService(config).generate()
        filename = f"setup_{config.project_name}.sh"
        return PlainTextResponse(
            content=script,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except Exception as exc:
        logger.exception("Script generation failed")
        raise HTTPException(
            status_code=500, detail=f"Script generation failed: {exc}"
        ) from exc
