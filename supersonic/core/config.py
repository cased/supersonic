from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class MergeStrategy(str, Enum):
    MERGE = "merge"
    SQUASH = "squash"
    REBASE = "rebase"


class PRConfig(BaseModel):
    """Configuration for Pull Request creation"""

    title: str = "Automated changes"
    description: Optional[str] = None
    base_branch: str = "main"
    draft: bool = False
    labels: List[str] = Field(default_factory=list)
    reviewers: List[str] = Field(default_factory=list)
    team_reviewers: List[str] = Field(default_factory=list)
    merge_strategy: MergeStrategy = MergeStrategy.SQUASH
    delete_branch_on_merge: bool = True
    auto_merge: bool = False


class SupersonicConfig(BaseModel):
    """Main configuration for Supersonic"""

    github_token: str
    base_url: str = "https://api.github.com"
    app_name: Optional[str] = None
    default_pr_config: PRConfig = Field(default_factory=PRConfig)
