from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any
from models.project_config import ProjectConfig

FileTree = Dict[str, str]

class ProjectBuilderBase(ABC):
    """Base class for all project type scavengers."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config

    @abstractmethod
    def build(self, tree: FileTree) -> None:
        """Add files to the tree."""
        pass
