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
    path: str
    original_content: str = ""
    new_content: str = ""
    old_file: str = ""
    new_file: str = ""
    hunks: List[DiffHunk] = None
    is_new: bool = False
    is_delete: bool = False
    is_new_file: bool = False
    is_deletion: bool = False
    mode_change: Optional[str] = None
    binary: bool = False

    def __post_init__(self):
        # Ensure hunks is never None
        if self.hunks is None:
            self.hunks = []
        # Sync old/new names
        if not self.old_file:
            self.old_file = self.path
        if not self.new_file:
            self.new_file = self.path
        # Sync deletion flags
        self.is_delete = self.is_deletion


class DiffParser:
    """Parse and analyze git diffs"""

    def parse(self, diff_content: str) -> List[FileDiff]:
        """Parse diff content into FileDiff objects"""
        diffs = []
        current_file = None
        current_hunk = None
        current_hunks = []

        lines = diff_content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]

            if line.startswith("diff --git"):
                if current_file and current_hunks:
                    diffs.append(
                        FileDiff(
                            path=current_file,
                            hunks=current_hunks,
                            is_new=False,
                            is_delete=False,
                        )
                    )
                current_file = self._extract_file_path(line)
                current_hunks = []
                current_hunk = None

                # Skip headers
                while i < len(lines) and not lines[i].startswith("@@"):
                    i += 1
                continue

            if line.startswith("@@"):
                if current_hunk:
                    current_hunks.append(current_hunk)
                match = re.match(r"^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", line)
                if match:
                    current_hunk = DiffHunk(
                        old_start=int(match.group(1)),
                        old_count=int(match.group(2) or 1),
                        new_start=int(match.group(3)),
                        new_count=int(match.group(4) or 1),
                        content=[],
                    )
                i += 1
                continue

            if current_hunk is not None:
                current_hunk.content.append(line)

            i += 1

        if current_file and current_hunk:
            current_hunks.append(current_hunk)
            diffs.append(
                FileDiff(
                    path=current_file,
                    hunks=current_hunks,
                    is_new=False,
                    is_delete=False,
                )
            )

        return diffs

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

        return FileDiff(path=match.group(2), hunks=[], is_new=False, is_delete=False)

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
