# granite/utils/git.py
from typing import Optional, List, Dict, Union
from pathlib import Path
import asyncio
import aiohttp
from github import Github
from git import Repo
import tempfile
import os

from granite.core.errors import GitError


class GitHandler:
    """Handle git operations and GitHub API interactions"""

    def __init__(self, token: str, base_url: Optional[str] = None):
        self.token = token
        self.base_url = base_url
        self.github = Github(token, base_url=base_url)
        self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                }
            )
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
                repo_obj.update_file(
                    path=path,
                    message=message,
                    content=content,
                    sha=contents.sha,
                    branch=branch,
                )
            except Exception:
                # File doesn't exist, create it
                repo_obj.create_file(
                    path=path, message=message, content=content, branch=branch
                )
        except Exception as e:
            raise GitError(f"Failed to update file: {e}")

    async def get_local_diff(
        self, path: Union[str, Path], files: Optional[List[str]] = None
    ) -> str:
        """Get diff from local repository"""
        try:
            repo = Repo(path)
            if files:
                return repo.git.diff("HEAD", "--", *files)
            return repo.git.diff("HEAD")
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
                if branch in local_repo.refs:
                    local_repo.git.checkout(branch)
                else:
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


# granite/utils/diff.py
import re
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    content: List[str]


@dataclass
class FileDiff:
    old_file: str
    new_file: str
    hunks: List[DiffHunk]
    is_new: bool
    is_delete: bool
    mode_change: Optional[str] = None


class DiffParser:
    """Parse and analyze git diffs"""

    def parse(self, diff_content: str) -> Dict[str, str]:
        """Parse diff content into a dict of file paths and their new content"""
        changes = {}
        current_file = None
        current_content = []

        lines = diff_content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]

            if line.startswith("diff --git"):
                if current_file:
                    changes[current_file] = "\n".join(current_content)
                current_file = self._extract_file_path(line)
                current_content = []

                # Skip until we find the actual changes
                while i < len(lines) and not lines[i].startswith("@@"):
                    i += 1
                continue

            if line.startswith("@@"):
                # Parse hunk header
                i += 1
                continue

            if line.startswith("+") and not line.startswith("+++"):
                # Add line (remove the '+' prefix)
                current_content.append(line[1:])
            elif not line.startswith("-") and not line.startswith("---"):
                # Context line
                current_content.append(line)

            i += 1

        if current_file:
            changes[current_file] = "\n".join(current_content)

        return changes

    def _extract_file_path(self, diff_header: str) -> str:
        """Extract the file path from a diff header line"""
        match = re.match(r"diff --git a/(.*) b/(.*)", diff_header)
        if match:
            return match.group(2)
        return ""

    def parse_detailed(self, diff_content: str) -> List[FileDiff]:
        """Parse diff content into detailed FileDiff objects"""
        diffs = []
        current_diff = None
        current_hunk = None

        for line in diff_content.splitlines():
            if line.startswith("diff --git"):
                if current_diff:
                    diffs.append(current_diff)
                current_diff = self._parse_diff_header(line)
            elif line.startswith("@@"):
                if current_hunk:
                    current_diff.hunks.append(current_hunk)
                current_hunk = self._parse_hunk_header(line)
            elif current_hunk is not None:
                current_hunk.content.append(line)

        if current_hunk:
            current_diff.hunks.append(current_hunk)
        if current_diff:
            diffs.append(current_diff)

        return diffs

    def _parse_diff_header(self, line: str) -> FileDiff:
        """Parse a diff header line into a FileDiff object"""
        match = re.match(r"diff --git a/(.*) b/(.*)", line)
        if not match:
            raise ValueError(f"Invalid diff header: {line}")

        return FileDiff(
            old_file=match.group(1),
            new_file=match.group(2),
            hunks=[],
            is_new=False,
            is_delete=False,
        )

    def _parse_hunk_header(self, line: str) -> DiffHunk:
        """Parse a hunk header line into a DiffHunk object"""
        match = re.match(r"^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", line)
        if not match:
            raise ValueError(f"Invalid hunk header: {line}")

        return DiffHunk(
            old_start=int(match.group(1)),
            old_count=int(match.group(2) or 1),
            new_start=int(match.group(3)),
            new_count=int(match.group(4) or 1),
            content=[],
        )

    def suggest_pr_details(self, changes: Dict[str, str]) -> Tuple[str, str]:
        """Generate PR title and description from changes"""
        files = list(changes.keys())

        if len(files) == 1:
            file = files[0]
            file_type = Path(file).suffix.lstrip(".") or "file"
            content_lines = changes[file].splitlines()

            # Try to find a meaningful change description
            if len(content_lines) > 0:
                first_line = content_lines[0].strip()
                if first_line.startswith(("#", "class ", "def ", "function")):
                    change_desc = first_line[:40]
                else:
                    change_desc = f"Update {file_type} content"

                return (
                    f"Update {file}: {change_desc}",
                    f"Modified {file} with the following changes:\n\n"
                    + "```\n"
                    + "\n".join(content_lines[:5])
                    + ("\n..." if len(content_lines) > 5 else "")
                    + "\n```",
                )

        # Multiple files changed
        file_types = set(Path(f).suffix.lstrip(".") or "file" for f in files)
        if len(file_types) == 1:
            file_type = next(iter(file_types))
            return (
                f"Update {len(files)} {file_type} files",
                "Modified files:\n" + "\n".join(f"- {f}" for f in files),
            )
        else:
            return (
                f"Update {len(files)} files",
                "Modified files:\n" + "\n".join(f"- {f}" for f in files),
            )
