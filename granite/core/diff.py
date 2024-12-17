# granite/core/diff.py
from typing import List, Tuple, Optional
from dataclasses import dataclass
import re
from pathlib import Path


@dataclass
class FileDiff:
    """Represents changes to a single file"""

    path: str
    original_content: Optional[str]
    new_content: Optional[str]
    is_new_file: bool
    is_deletion: bool
    mode_change: Optional[str] = None
    binary: bool = False


@dataclass
class DiffHunk:
    """Represents a single hunk of changes in a diff"""

    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    content: List[str]


class DiffParser:
    """Parse and analyze git diffs"""

    def parse(self, diff_content: str) -> List[FileDiff]:
        """
        Parse a git diff into a list of file changes.

        Args:
            diff_content: The git diff string

        Returns:
            List of FileDiff objects representing each changed file

        Example diff format:
            diff --git a/file.txt b/file.txt
            index abc..def
            --- a/file.txt
            +++ b/file.txt
            @@ -1,3 +1,3 @@
            -old content
            +new content
        """
        diffs: List[FileDiff] = []
        current_file: Optional[FileDiff] = None
        current_content: List[str] = []
        current_original: List[str] = []
        in_hunk = False

        for line in diff_content.splitlines():
            # Start of a new file's diff
            if line.startswith("diff --git"):
                # Save previous file if exists
                if current_file:
                    if current_content:
                        current_file.new_content = "\n".join(current_content)
                    if current_original:
                        current_file.original_content = "\n".join(current_original)
                    diffs.append(current_file)

                # Start new file
                file_path = self._extract_file_path(line)
                current_file = FileDiff(
                    path=file_path,
                    original_content=None,
                    new_content=None,
                    is_new_file=False,
                    is_deletion=False,
                    binary=False,
                )
                current_content = []
                current_original = []
                in_hunk = False

            # File metadata
            elif line.startswith("new file mode"):
                if current_file:
                    current_file.is_new_file = True
                    current_file.mode_change = line.split()[-1]
            elif line.startswith("deleted file mode"):
                if current_file:
                    current_file.is_deletion = True
                    current_file.mode_change = line.split()[-1]
            elif line.startswith("Binary files"):
                if current_file:
                    current_file.binary = True

            # Start of file content
            elif line.startswith("---") or line.startswith("+++"):
                continue
            elif line.startswith("@@"):
                in_hunk = True
                continue

            # File content
            elif in_hunk and current_file and not current_file.binary:
                if line.startswith("+"):
                    current_content.append(line[1:])
                elif line.startswith("-"):
                    current_original.append(line[1:])
                elif not line.startswith("\\"):  # Ignore no newline markers
                    current_content.append(line)
                    current_original.append(line)

        # Add the last file
        if current_file:
            if current_content:
                current_file.new_content = "\n".join(current_content)
            if current_original:
                current_file.original_content = "\n".join(current_original)
            diffs.append(current_file)

        return diffs

    def parse_detailed(
        self, diff_content: str
    ) -> List[Tuple[FileDiff, List[DiffHunk]]]:
        """
        Parse a diff with detailed hunk information.
        Useful for more granular analysis of changes.
        """
        result: List[Tuple[FileDiff, List[DiffHunk]]] = []
        current_file: Optional[FileDiff] = None
        current_hunks: List[DiffHunk] = []
        current_hunk: Optional[DiffHunk] = None

        for line in diff_content.splitlines():
            if line.startswith("diff --git"):
                if current_file:
                    result.append((current_file, current_hunks))
                current_file = FileDiff(
                    path=self._extract_file_path(line),
                    original_content=None,
                    new_content=None,
                    is_new_file=False,
                    is_deletion=False,
                )
                current_hunks = []

            elif line.startswith("new file mode"):
                if current_file:
                    current_file.is_new_file = True
            elif line.startswith("deleted file mode"):
                if current_file:
                    current_file.is_deletion = True

            elif line.startswith("@@"):
                if current_hunk:
                    current_hunks.append(current_hunk)
                # Parse hunk header: @@ -1,3 +1,3 @@
                match = re.match(r"^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", line)
                if match:
                    current_hunk = DiffHunk(
                        old_start=int(match.group(1)),
                        old_lines=int(match.group(2) or 1),
                        new_start=int(match.group(3)),
                        new_lines=int(match.group(4) or 1),
                        content=[],
                    )

            elif current_hunk is not None:
                current_hunk.content.append(line)

        # Add the last file and hunk
        if current_hunk:
            current_hunks.append(current_hunk)
        if current_file:
            result.append((current_file, current_hunks))

        return result

    def _extract_file_path(self, diff_header: str) -> str:
        """Extract the file path from a diff header line"""
        match = re.match(r"diff --git a/(.*) b/(.*)", diff_header)
        if match:
            return match.group(2)
        return ""

    def generate_commit_message(self, diffs: List[FileDiff]) -> str:
        """
        Generate a descriptive commit message from the changes.
        Tries to create meaningful titles based on the changes made.
        """
        if len(diffs) == 1:
            diff = diffs[0]
            file_type = Path(diff.path).suffix.lstrip(".") or "file"

            # Special handling for common file types
            if file_type == "md" and diff.new_content:
                # Look for markdown headers
                first_line = diff.new_content.split("\n")[0].strip()
                if first_line.startswith("# "):
                    return f"Update documentation: {first_line[2:]}"

            if file_type in ("py", "js", "ts", "java", "rb"):
                # Look for function/class definitions
                if diff.new_content:
                    lines = diff.new_content.split("\n")
                    for line in lines:
                        if any(
                            pattern in line.lower()
                            for pattern in ("def ", "class ", "function", "interface")
                        ):
                            return f"Update {file_type}: {line.strip()}"

            # Default single file message
            action = (
                "Add"
                if diff.is_new_file
                else "Delete"
                if diff.is_deletion
                else "Update"
            )
            return f"{action} {diff.path}"
        else:
            # Multiple file changes
            counts = {
                "added": len([d for d in diffs if d.is_new_file]),
                "deleted": len([d for d in diffs if d.is_deletion]),
                "modified": len(
                    [d for d in diffs if not (d.is_new_file or d.is_deletion)]
                ),
            }

            # Try to group by file type
            file_types = set(Path(d.path).suffix.lstrip(".") for d in diffs)
            if len(file_types) == 1:
                file_type = next(iter(file_types)) or "files"
                total = sum(counts.values())
                return f"Update {total} {file_type} files"

            # Default multiple file message
            parts = []
            if counts["added"]:
                parts.append(f"Add {counts['added']} files")
            if counts["deleted"]:
                parts.append(f"Delete {counts['deleted']} files")
            if counts["modified"]:
                parts.append(f"Update {counts['modified']} files")
            return ", ".join(parts)

    def suggest_pr_details(self, diffs: List[FileDiff]) -> Tuple[str, str]:
        """
        Generate a PR title and description from the changes.
        Returns (title, description) tuple.
        """
        title = self.generate_commit_message(diffs)

        # Generate detailed description
        description = ["## Changes\n"]

        for diff in diffs:
            # Add file change header with emoji
            if diff.is_new_file:
                description.append(f"✨ Added `{diff.path}`")
            elif diff.is_deletion:
                description.append(f"🗑️ Deleted `{diff.path}`")
            else:
                description.append(f"📝 Modified `{diff.path}`")

            # Add preview for text files
            if not diff.binary and diff.new_content and self._is_text_file(diff.path):
                preview_lines = diff.new_content.split("\n")[:5]
                if preview_lines:
                    description.append("\n```" + self._get_file_type(diff.path))
                    description.extend(preview_lines)
                    if len(diff.new_content.split("\n")) > 5:
                        description.append("...")
                    description.append("```")

            description.append("")  # Add blank line between files

        return title, "\n".join(description)

    def _is_text_file(self, path: str) -> bool:
        """Check if a file is likely to be text based on extension"""
        text_extensions = {
            ".txt",
            ".md",
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".html",
            ".css",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".rs",
            ".go",
            ".java",
            ".kt",
            ".rb",
            ".php",
        }
        return Path(path).suffix.lower() in text_extensions

    def _get_file_type(self, path: str) -> str:
        """Get the syntax highlighting type for a file"""
        ext = Path(path).suffix.lstrip(".")
        ext_to_type = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "jsx": "javascript",
            "tsx": "typescript",
            "md": "markdown",
            "html": "html",
            "css": "css",
            "json": "json",
            "yaml": "yaml",
            "yml": "yaml",
            "toml": "toml",
            "rs": "rust",
            "go": "go",
            "java": "java",
            "kt": "kotlin",
            "rb": "ruby",
            "php": "php",
        }
        return ext_to_type.get(ext, "")
