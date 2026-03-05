from __future__ import annotations
from .base import FileTree
from .common import CommonFilesBuilder
from .fastapi_builder import FastApiBuilder
from .flask_builder import FlaskBuilder
from .django_builder import DjangoBuilder
from .other_builders import CliBuilder, LibraryBuilder, DataScienceBuilder
from models.project_config import ProjectConfig

class ProjectBuilder:
    """Main orchestrator for project scaffolding."""

    def __init__(self, config: ProjectConfig):
        self.config = config

    def build(self) -> FileTree:
        """Return a dict of {relative_path: content} for the scaffolded project."""
        tree: FileTree = {}
        
        # 1. Add common files
        CommonFilesBuilder(self.config).build(tree)
        
        # 2. Add project-type-specific files
        self._add_project_type_files(tree)
        
        return tree

    def _add_project_type_files(self, tree: FileTree) -> None:
        pt = self.config.project_type
        
        if pt == "web-api":
            fw = self.config.framework or "fastapi"
            if fw == "fastapi":
                FastApiBuilder(self.config).build(tree)
            elif fw == "flask":
                FlaskBuilder(self.config).build(tree)
            elif fw == "django":
                DjangoBuilder(self.config).build(tree)
        elif pt == "cli":
            CliBuilder(self.config).build(tree)
        elif pt == "library":
            LibraryBuilder(self.config).build(tree)
        elif pt == "ml":
            DataScienceBuilder(self.config).build(tree)

def build_project(config: ProjectConfig) -> FileTree:
    """Legacy function interface for project scaffolding."""
    return ProjectBuilder(config).build()
