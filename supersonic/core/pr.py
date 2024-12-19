from typing import Optional, Union, Dict, List, Mapping
from pathlib import Path
import time

from .config import SupersonicConfig, PRConfig
from .errors import GitHubError
from .diff import FileDiff
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

    def create_pr(
        self,
        repo: str,
        changes: Dict[str, Optional[str]],
        config: Optional[Union[PRConfig, Dict]] = None,
        branch_name: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Create a PR with the specified changes.
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
                branch_name = f"{self.config.app_name or 'Supersonic'}/{timestamp}"

            # Create branch
            self.github.create_branch(
                repo=repo, branch=branch_name, base_branch=config.base_branch
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
                self.github.add_labels(repo, pr_number, config.labels)

            # Add reviewers if specified
            if config.reviewers:
                self.github.add_reviewers(repo, pr_number, config.reviewers)

            # Enable auto-merge if requested
            if config.auto_merge:
                self.github.enable_auto_merge(
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

    def create_pr_from_file(
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
            return self.create_pr(
                repo=repo, changes={upstream_path: content}, config=kwargs
            )
        except Exception as e:
            raise GitHubError(f"Failed to update file: {e}")

    def create_pr_from_multiple_contents(
        self,
        repo: str,
        contents: Mapping[str, str],  # Changed from Dict to Mapping
        title: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Create a PR to update multiple files with provided content.

        Args:
            repo: Repository name (owner/repo)
            contents: Dict mapping file paths to their content
                    e.g. {"path/to/file.py": "print('hello')",
                         "docs/README.md": "# Title"}
            title: PR title
            **kwargs: Additional PR options (draft, labels, etc)

        Returns:
            URL of the created PR
        """
        try:
            # Convert to Dict[str, Optional[str]] for create_pr
            changes: Dict[str, Optional[str]] = {k: v for k, v in contents.items()}
            return self.create_pr(repo=repo, changes=changes, config=kwargs)
        except Exception as e:
            raise GitHubError(f"Failed to update files: {e}")

    def create_pr_from_content(
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
            return self.create_pr(
                repo=repo, changes={path: content}, config=kwargs
            )
        except Exception as e:
            raise GitHubError(f"Failed to update content: {e}")

    def create_pr_from_files(
        self,
        repo: str,
        files: Mapping[str, str],  # Changed from Dict to Mapping
        **kwargs,
    ) -> str:
        """
        Create a PR to update multiple files from local files.

        Args:
            repo: Repository name (owner/repo)
            files: Dict mapping local file paths to their upstream paths
                   e.g. {"local/config.json": "config/settings.json",
                        "docs/local.md": "docs/README.md"}
            **kwargs: Additional PR options (title, draft, etc)

        Returns:
            URL of the created PR
        """
        try:
            # Read all local files
            contents: Dict[str, Optional[str]] = {}
            for local_path, upstream_path in files.items():
                try:
                    content = Path(local_path).read_text()
                    contents[upstream_path] = content
                except Exception as e:
                    raise GitHubError(f"Failed to read file {local_path}: {e}")

            # Create PR with all file contents
            return self.create_pr(repo=repo, changes=contents, config=kwargs)
        except Exception as e:
            raise GitHubError(f"Failed to update files: {e}")
