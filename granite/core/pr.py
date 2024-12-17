from typing import Optional, Union, Dict, List
from pathlib import Path
import time
import uuid
import asyncio
from datetime import datetime

from .config import GraniteConfig, PRConfig
from .errors import GitHubError, ConfigError
from .diff import FileDiff
from .github import GitHubAPI


class Granite:
    """Main class for Granite PR operations"""

    def __init__(self, config: Union[GraniteConfig, Dict, str], **kwargs):
        """
        Initialize Granite with configuration.

        Args:
            config: Either a GraniteConfig object, dict of config values,
                   or a GitHub token string
            **kwargs: Additional configuration options
        """
        if isinstance(config, str):
            self.config = GraniteConfig(github_token=config, **kwargs)
        elif isinstance(config, dict):
            self.config = GraniteConfig(**config, **kwargs)
        else:
            self.config = config

        self.github = GitHubAPI(self.config.github_token, self.config.base_url)

    async def create_pr(
        self,
        repo: str,
        changes: Dict[str, Optional[str]],
        config: Optional[Union[PRConfig, Dict]] = None,
        branch_name: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Create a PR with the specified changes.

        Args:
            repo: Repository name (owner/repo)
            changes: Dict of file paths and their new content (None for deletion)
            config: PR configuration
            branch_name: Name for the new branch (generated if not provided)
            **kwargs: Additional options

        Returns:
            URL of the created PR
        """
        try:
            # Process configuration
            if isinstance(config, dict):
                config = PRConfig(**config)
            elif config is None:
                config = self.config.default_pr_config

            # Generate branch name if not provided
            if branch_name is None:
                timestamp = int(time.time())
                branch_name = f"{self.config.app_name or 'granite'}/{timestamp}"

            # Create branch
            await self.github.create_branch(
                repo=repo, branch=branch_name, base_branch=config.base_branch
            )

            # Create/update/delete files
            for path, content in changes.items():
                message = f"{'Update' if content is not None else 'Delete'} {path}"
                await self.github.update_file(
                    repo=repo,
                    path=path,
                    content=content,
                    message=message,
                    branch=branch_name,
                )

            # Create PR
            pr_url = await self.github.create_pull_request(
                repo=repo,
                title=config.title,
                body=config.description or "",
                head=branch_name,
                base=config.base_branch,
                draft=config.draft,
            )

            # Extract PR number from URL
            pr_number = int(pr_url.split("/")[-1])

            # Add labels if specified
            if config.labels:
                await self.github.add_labels(repo, pr_number, config.labels)

            # Add reviewers if specified
            if config.reviewers:
                await self.github.add_reviewers(repo, pr_number, config.reviewers)

            # Enable auto-merge if requested
            if config.auto_merge:
                await self.github.enable_auto_merge(
                    repo=repo, pr_number=pr_number, merge_method=config.merge_strategy
                )

            return pr_url

        except Exception as e:
            raise GitHubError(f"Failed to create PR: {e}")

    def _generate_diff_description(self, file_diffs: List[FileDiff]) -> str:
        """Generate PR description from file diffs"""
        description = []
        for diff in file_diffs:
            if diff.is_deletion:
                description.append(f"- Delete {diff.path}")
            else:
                description.append(f"- Update {diff.path}")
                if diff.new_content:
                    description.append("```")
                    description.append(
                        diff.new_content[:200]
                        + ("..." if len(diff.new_content) > 200 else "")
                    )
                    description.append("```")
        return "\n".join(description)

    async def create_pr_from_local(
        self,
        repo: str,
        path: Union[str, Path],
        files: Optional[List[str]] = None,
        config: Optional[Union[PRConfig, Dict]] = None,
        **kwargs,
    ) -> str:
        """Create PR from local directory changes"""
        try:
            # Get diff from local changes
            diff = await self.github.get_local_diff(path, files)

            # Create PR from diff
            return await self.create_pr_from_diff(
                repo=repo, diff=diff, config=config, **kwargs
            )
        except Exception as e:
            raise GitHubError(f"Failed to create PR from local changes: {e}")

    async def create_pr_from_file(
        self, repo: str, local_file_path: str, upstream_path: str, **kwargs
    ) -> str:
        """
        Create a PR to update a file in a repository.

        Args:
            repo: Repository name (owner/repo)
            local_file_path: Path to local file
            upstream_path: Where to put the file in the repo
            **kwargs: Additional PR options (title, draft, etc)

        Returns:
            URL of the created PR
        """
        try:
            # Read local file
            content = Path(local_file_path).read_text()

            # Create PR with single file change
            return await self.create_pr(
                repo=repo, changes={upstream_path: content}, config=kwargs
            )
        except Exception as e:
            raise GitHubError(f"Failed to update file: {e}")

    async def create_pr_from_files(
        self, repo: str, files: Dict[str, str], **kwargs
    ) -> str:
        """
        Create a PR to update multiple files with provided content.

        Args:
            repo: Repository name (owner/repo)
            files: Dict mapping file paths to their content
                  e.g. {"path/to/file.py": "print('hello')",
                       "docs/README.md": "# Title"}
            **kwargs: Additional PR options (title, draft, etc)

        Returns:
            URL of the created PR
        """
        try:
            return await self.create_pr(repo=repo, changes=files, config=kwargs)
        except Exception as e:
            raise GitHubError(f"Failed to update files: {e}")

    async def create_pr_from_content(
        self, repo: str, content: str, path: str, **kwargs
    ) -> str:
        """
        Create a PR to update a file with provided content.

        Args:
            repo: Repository name (owner/repo)
            content: The new file content as a string
            path: Where to put the file in the repo
            **kwargs: Additional PR options (title, draft, etc)

        Returns:
            URL of the created PR
        """
        try:
            return await self.create_pr(
                repo=repo, changes={path: content}, config=kwargs
            )
        except Exception as e:
            raise GitHubError(f"Failed to update content: {e}")
