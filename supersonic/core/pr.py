from typing import Optional, Union, Dict, Mapping, Any
from pathlib import Path
import time

from .config import SupersonicConfig, PRConfig
from .errors import GitHubError
from .github import GitHubAPI
from ..utils import GitClient


class Supersonic:
    """Main class for Supersonic PR operations"""

    def __init__(
        self,
        config: SupersonicConfig,
        github_api: Optional[GitHubAPI] = None,
        git_client: Optional[GitClient] = None,
    ) -> None:
        """Initialize PR creator"""
        self.config = config
        self.github = github_api or GitHubAPI(token=config.github_token, base_url=config.base_url)
        self.git = git_client or GitClient()

    def _prepare_pr_config(
        self,
        pr_config: Optional[Union[PRConfig, Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> PRConfig:
        """Prepare PR configuration"""
        if pr_config is not None:
            if kwargs:
                raise ValueError(
                    "Cannot provide both PRConfig and keyword arguments. Choose one approach."
                )
            if isinstance(pr_config, dict):
                return PRConfig(**pr_config)
            return pr_config

        # If kwargs are provided, create PRConfig from them
        if kwargs:
            return PRConfig(**kwargs)

        # If neither is provided, use defaults
        return self.config.default_pr_config

    def create_pr(
        self,
        repo: str,
        changes: Dict[str, Optional[str]],
        config: Optional[Union[PRConfig, Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> str:
        """Create a PR with the specified changes."""
        # Get configuration (either from config object or kwargs)
        # This is outside the try/except so ValueError bubbles up directly
        pr_config = self._prepare_pr_config(pr_config=config, **kwargs)

        try:
            # Generate branch name
            timestamp = int(time.time())
            branch_name = f"{self.config.app_name or 'supersonic'}/{timestamp}"

            # Create branch
            self.github.create_branch(
                repo=repo, branch=branch_name, base_branch=pr_config.base_branch
            )

            # Create/update/delete files
            for path, content in changes.items():
                message = f"{'Update' if content is not None else 'Delete'} {path}"
                self.github.update_file(
                    repo=repo,
                    path=path,
                    content=content,
                    message=message,
                    branch=branch_name,
                )

            # Create PR
            pr_url = self.github.create_pull_request(
                repo=repo,
                title=pr_config.title,
                body=pr_config.description or "",
                head=branch_name,
                base=pr_config.base_branch,
                draft=pr_config.draft,
            )

            # Extract PR number from URL
            pr_number = int(pr_url.split("/")[-1])

            # Add labels if specified
            if pr_config.labels:
                self.github.add_labels(repo, pr_number, pr_config.labels)

            # Add reviewers if specified
            if pr_config.reviewers:
                self.github.add_reviewers(repo, pr_number, pr_config.reviewers)

            # Enable auto-merge if requested
            if getattr(pr_config, "auto_merge", False):
                self.github.enable_auto_merge(
                    repo=repo,
                    pr_number=pr_number,
                    merge_method=getattr(pr_config, "merge_strategy", "squash"),
                )

            return pr_url

        except Exception as e:
            raise GitHubError(f"Failed to create PR: {e}")

    def create_pr_from_file(
        self,
        repo: str,
        local_file_path: str,
        upstream_path: str,
        title: Optional[str] = None,
        draft: bool = False,
    ) -> str:
        """Create PR from local file"""
        try:
            content = Path(local_file_path).read_text()
            return self.create_pr(repo=repo, changes={upstream_path: content}, title=title, draft=draft)
        except Exception as e:
            raise GitHubError(f"Failed to update file: {e}")

    def create_pr_from_content(
        self,
        repo: str,
        content: str,
        upstream_path: str,
        title: Optional[str] = None,
        draft: bool = False,
        **kwargs: Any,
    ) -> str:
        """Create PR from content"""
        try:
            # Check for unknown kwargs before passing to create_pr
            valid_kwargs = {'title', 'draft', 'description', 'base_branch', 'labels', 'reviewers', 'team_reviewers', 'merge_strategy', 'delete_branch_on_merge', 'auto_merge'}
            unknown_kwargs = set(kwargs.keys()) - valid_kwargs
            if unknown_kwargs:
                raise ValueError(f"Unknown arguments: {', '.join(unknown_kwargs)}")

            return self.create_pr(
                repo=repo,
                changes={upstream_path: content},
                title=title or "Update file",  # Provide default title
                draft=draft,
                **kwargs
            )
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise GitHubError(f"Failed to update content: {e}")

    def create_pr_from_multiple_contents(
        self,
        repo: str,
        contents: Mapping[str, str],
        title: Optional[str] = None,
        draft: bool = False,
        **kwargs: Any,
    ) -> str:
        """Create a PR to update multiple files with provided content."""
        try:
            changes: Dict[str, Optional[str]] = {k: v for k, v in contents.items()}
            return self.create_pr(repo=repo, changes=changes, title=title, draft=draft, **kwargs)
        except Exception as e:
            raise GitHubError(f"Failed to update files: {e}")

    def create_pr_from_files(
        self,
        repo: str,
        files: Mapping[str, str],
        title: Optional[str] = None,
        draft: bool = False,
        **kwargs: Any,
    ) -> str:
        """Create a PR to update multiple files from local files."""
        try:
            contents: Dict[str, Optional[str]] = {}
            for local_path, upstream_path in files.items():
                try:
                    content = Path(local_path).read_text()
                    contents[upstream_path] = content
                except Exception as e:
                    raise GitHubError(f"Failed to read file {local_path}: {e}")

            return self.create_pr(repo=repo, changes=contents, title=title, draft=draft, **kwargs)
        except Exception as e:
            raise GitHubError(f"Failed to update files: {e}")
