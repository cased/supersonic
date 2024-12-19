from typing import Optional, Union, Dict, Mapping
from pathlib import Path
import time

from .config import SupersonicConfig, PRConfig
from .errors import GitHubError
from .github import GitHubAPI


class Supersonic:
    """Main class for Supersonic PR operations"""

    def __init__(self, config: Union[SupersonicConfig, Dict, str], **kwargs):
        """
        Initialize Supersonic with configuration.

        Args:
            config: Either a SupersonicConfig object, dict of config values,
                   or a GitHub token string
            **kwargs: Additional configuration options
        """
        if isinstance(config, str):
            self.config = SupersonicConfig(github_token=config, **kwargs)
        elif isinstance(config, dict):
            self.config = SupersonicConfig(**config, **kwargs)
        else:
            self.config = config

        self.github = GitHubAPI(self.config.github_token, self.config.base_url)

    def _prepare_pr_config(
        self, 
        pr_config: Optional[Union[PRConfig, Dict]] = None, 
        **kwargs
    ) -> PRConfig:
        """
        Prepares PR configuration, either from a PRConfig/dict or from kwargs.
        Cannot mix both approaches.

        Args:
            pr_config: Optional PRConfig object or dict
            **kwargs: Configuration options passed as keyword arguments

        Returns:
            PRConfig object with the configuration to use

        Raises:
            ValueError: If both pr_config and kwargs are provided
        """
        if pr_config is not None:
            if kwargs:
                raise ValueError("Cannot provide both PRConfig and keyword arguments. Choose one approach.")
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
        config: Optional[Union[PRConfig, Dict]] = None,
        **kwargs
    ) -> str:
        """
        Create a PR with the specified changes.

        Args:
            repo: Repository name (owner/repo)
            changes: Dict mapping file paths to their new content
            config: Optional PRConfig object or dict for full configuration
            **kwargs: PR options (title, description, draft, etc.)

        Returns:
            URL of the created PR

        Raises:
            ValueError: If both config and kwargs are provided
            GitHubError: If PR creation fails
        """
        # Get configuration (either from config object or kwargs)
        # This is outside the try/except so ValueError bubbles up directly
        pr_config = self._prepare_pr_config(pr_config=config, **kwargs)

        try:
            # Generate branch name
            timestamp = int(time.time())
            branch_name = f"{self.config.app_name or 'supersonic'}/{timestamp}"

            # Create branch
            self.github.create_branch(
                repo=repo,
                branch=branch_name,
                base_branch=pr_config.base_branch
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
            if getattr(pr_config, 'auto_merge', False):
                self.github.enable_auto_merge(
                    repo=repo,
                    pr_number=pr_number,
                    merge_method=getattr(pr_config, 'merge_strategy', 'squash')
                )

            return pr_url

        except Exception as e:
            raise GitHubError(f"Failed to create PR: {e}")

    def create_pr_from_file(
        self, 
        repo: str, 
        local_file_path: str, 
        upstream_path: str, 
        **kwargs
    ) -> str:
        """
        Create a PR from a local file.

        Args:
            repo: Repository name (owner/repo)
            local_file_path: Path to local file
            upstream_path: Where to put the file in the repo
            **kwargs: PR options (title, description, draft, etc.)

        Returns:
            URL of the created PR
        """
        try:
            content = Path(local_file_path).read_text()
            return self.create_pr(
                repo=repo,
                changes={upstream_path: content},
                **kwargs
            )
        except Exception as e:
            raise GitHubError(f"Failed to update file: {e}")

    def create_pr_from_content(
        self, 
        repo: str, 
        content: str, 
        path: str, 
        **kwargs
    ) -> str:
        """
        Create a PR to update a single file with provided content.

        Args:
            repo: Repository name (owner/repo)
            content: The new file content
            path: Where to put the file in the repo
            **kwargs: PR options (title, description, draft, etc.)

        Returns:
            URL of the created PR
        """
        try:
            return self.create_pr(
                repo=repo,
                changes={path: content},
                **kwargs
            )
        except Exception as e:
            raise GitHubError(f"Failed to update content: {e}")

    def create_pr_from_multiple_contents(
        self,
        repo: str,
        contents: Mapping[str, str],
        **kwargs,
    ) -> str:
        """
        Create a PR to update multiple files with provided content.

        Args:
            repo: Repository name (owner/repo)
            contents: Dict mapping file paths to their content
            **kwargs: PR options (title, description, draft, etc.)

        Returns:
            URL of the created PR
        """
        try:
            changes: Dict[str, Optional[str]] = {k: v for k, v in contents.items()}
            return self.create_pr(
                repo=repo,
                changes=changes,
                **kwargs
            )
        except Exception as e:
            raise GitHubError(f"Failed to update files: {e}")

    def create_pr_from_files(
        self,
        repo: str,
        files: Mapping[str, str],
        **kwargs,
    ) -> str:
        """
        Create a PR to update multiple files from local files.

        Args:
            repo: Repository name (owner/repo)
            files: Dict mapping local file paths to their upstream paths
            **kwargs: PR options (title, description, draft, etc.)

        Returns:
            URL of the created PR
        """
        try:
            contents: Dict[str, Optional[str]] = {}
            for local_path, upstream_path in files.items():
                try:
                    content = Path(local_path).read_text()
                    contents[upstream_path] = content
                except Exception as e:
                    raise GitHubError(f"Failed to read file {local_path}: {e}")

            return self.create_pr(
                repo=repo,
                changes=contents,
                **kwargs
            )
        except Exception as e:
            raise GitHubError(f"Failed to update files: {e}")