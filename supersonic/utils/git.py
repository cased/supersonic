from typing import Optional, List, Union, cast
from pathlib import Path
import aiohttp
from github import Github
from github.ContentFile import ContentFile
from git import Repo
import tempfile
import os

from supersonic.core.errors import GitError


class GitHandler:
    """Handle git operations and GitHub API interactions"""

    def __init__(self, token: str, base_url: Optional[str] = None):
        self.token = token
        self.base_url = base_url
        if base_url:
            self.github = Github(token, base_url=base_url)
        else:
            self.github = Github(token)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                }
            )
        assert self._session is not None  # Help mypy understand _session is set
        return self._session

    async def create_branch(self, repo: str, branch: str, base: str) -> None:
        """Create a new branch from base"""
        try:
            session = await self._get_session()
            repo_obj = self.github.get_repo(repo)
            base_sha = repo_obj.get_branch(base).commit.sha

            url = f"https://api.github.com/repos/{repo}/git/refs"
            if self.base_url:
                url = f"{self.base_url}/repos/{repo}/git/refs"

            async with session.post(
                url, json={"ref": f"refs/heads/{branch}", "sha": base_sha}
            ) as response:
                if response.status not in (200, 201):
                    text = await response.text()
                    raise GitError(f"Failed to create branch: {text}")
        except Exception as e:
            raise GitError(f"Failed to create branch: {e}")

    async def update_file(
        self, repo: str, path: str, content: str, message: str, branch: str
    ) -> None:
        """Update or create a file in the repository"""
        try:
            repo_obj = self.github.get_repo(repo)
            try:
                # Try to get existing file
                contents = repo_obj.get_contents(path, ref=branch)
                if isinstance(contents, List):
                    raise GitError(f"Path '{path}' points to a directory")
                
                # At this point contents must be a ContentFile
                contents = cast(ContentFile, contents)
                repo_obj.update_file(
                    path=path,
                    message=message,
                    content=content,
                    sha=contents.sha,
                    branch=branch,
                )
            except Exception as e:
                if "Not Found" in str(e):
                    # File doesn't exist, create it
                    repo_obj.create_file(
                        path=path, message=message, content=content, branch=branch
                    )
                else:
                    raise
        except Exception as e:
            raise GitError(f"Failed to update file: {e}")

    async def get_local_diff(
        self, path: Union[str, Path], files: Optional[List[str]] = None
    ) -> str:
        """Get diff from local repository"""
        try:
            repo: Repo = Repo(path)
            if files:
                return str(repo.git.diff("HEAD", "--", *files))
            return str(repo.git.diff("HEAD"))
        except Exception as e:
            raise GitError(f"Failed to get local diff: {e}")

    async def apply_diff(self, repo: str, branch: str, diff_content: str) -> None:
        """Apply a diff to a branch"""
        try:
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Clone repository
                repo_obj = self.github.get_repo(repo)
                clone_url = repo_obj.clone_url.replace(
                    "https://", f"https://{self.token}@"
                )
                local_repo = Repo.clone_from(clone_url, temp_dir)

                # Checkout branch
                try:
                    local_repo.git.checkout(branch)
                except Exception:
                    # Branch doesn't exist, create it
                    local_repo.git.checkout("-b", branch)

                # Apply diff
                diff_path = os.path.join(temp_dir, "changes.diff")
                with open(diff_path, "w") as f:
                    f.write(diff_content)

                try:
                    local_repo.git.apply(diff_path)
                except Exception as e:
                    raise GitError(f"Failed to apply diff: {e}")

                # Commit and push changes
                local_repo.git.add(A=True)
                local_repo.index.commit("Apply changes")
                local_repo.git.push("origin", branch)

        except Exception as e:
            raise GitError(f"Failed to apply diff: {e}")
