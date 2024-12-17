import pytest
from click.testing import CliRunner
from unittest.mock import AsyncMock, patch
from pathlib import Path

from cli import cli
from supersonic.core.config import SupersonicConfig


@pytest.fixture
def runner():
    """Create a CLI test runner"""
    return CliRunner()


@pytest.fixture
def mock_supersonic():
    """Mock Supersonic class"""
    with patch("cli.Supersonic") as mock:
        # Set up async mock methods
        instance = mock.return_value
        instance.create_pr_from_file = AsyncMock()
        instance.create_pr_from_content = AsyncMock()
        instance.create_pr_from_files = AsyncMock()

        # Set default return value for PR creation (PR URL)
        pr_url = "https://github.com/owner/repo/pull/1"
        instance.create_pr_from_file.return_value = pr_url
        instance.create_pr_from_content.return_value = pr_url
        instance.create_pr_from_files.return_value = pr_url

        yield mock


def test_cli_requires_token(runner):
    """Test that CLI requires GitHub token"""
    result = runner.invoke(cli, ["update", "owner/repo", "file.txt"])
    assert result.exit_code != 0
    assert "Missing option '--token'" in result.output


def test_update_file(runner, mock_supersonic):
    """Test updating a single file"""
    with runner.isolated_filesystem():
        # Create a test file
        Path("test.txt").write_text("test content")

        result = runner.invoke(
            cli,
            [
                "--token",
                "test-token",
                "update",
                "owner/repo",
                "test.txt",
                "path/to/test.txt",
                "--title",
                "Update test file",
                "--draft",
            ],
        )

        assert result.exit_code == 0
        assert "Created PR:" in result.output

        # Verify Supersonic was called correctly
        mock_supersonic.assert_called_once_with(SupersonicConfig(github_token="test-token"))
        instance = mock_supersonic.return_value
        instance.create_pr_from_file.assert_called_once_with(
            repo="owner/repo",
            local_file_path="test.txt",
            upstream_path="path/to/test.txt",
            title="Update test file",
            draft=True,
        )


def test_update_file_default_path(runner, mock_supersonic):
    """Test updating a file using the local filename as path"""
    with runner.isolated_filesystem():
        Path("test.txt").write_text("test content")

        result = runner.invoke(
            cli, ["--token", "test-token", "update", "owner/repo", "test.txt"]
        )

        assert result.exit_code == 0
        instance = mock_supersonic.return_value
        instance.create_pr_from_file.assert_called_once_with(
            repo="owner/repo",
            local_file_path="test.txt",
            upstream_path="test.txt",
            title=None,
            draft=False,
        )


def test_update_content(runner, mock_supersonic):
    """Test updating content directly"""
    result = runner.invoke(
        cli,
        [
            "--token",
            "test-token",
            "update-content",
            "owner/repo",
            "Hello World",
            "README.md",
            "--title",
            "Update readme",
        ],
    )

    assert result.exit_code == 0
    instance = mock_supersonic.return_value
    instance.create_pr_from_content.assert_called_once_with(
        repo="owner/repo",
        content="Hello World",
        path="README.md",
        title="Update readme",
        draft=False,
    )


def test_update_files(runner, mock_supersonic):
    """Test updating multiple files"""
    with runner.isolated_filesystem():
        # Create test files
        Path("file1.txt").write_text("content 1")
        Path("file2.txt").write_text("content 2")

        result = runner.invoke(
            cli,
            [
                "--token",
                "test-token",
                "update-files",
                "owner/repo",
                "-f",
                "file1.txt",
                "path/to/file1.txt",
                "-f",
                "file2.txt",
                "path/to/file2.txt",
                "--title",
                "Update multiple files",
                "--draft",
            ],
        )

        assert result.exit_code == 0
        instance = mock_supersonic.return_value
        instance.create_pr_from_files.assert_called_once_with(
            repo="owner/repo",
            files={"path/to/file1.txt": "content 1", "path/to/file2.txt": "content 2"},
            title="Update multiple files",
            draft=True,
        )


def test_error_handling(runner, mock_supersonic):
    """Test error handling in CLI"""
    instance = mock_supersonic.return_value
    instance.create_pr_from_file.side_effect = Exception("API Error")

    with runner.isolated_filesystem():
        Path("test.txt").write_text("test content")

        result = runner.invoke(
            cli, ["--token", "test-token", "update", "owner/repo", "test.txt"]
        )

        assert result.exit_code != 0
        assert "Error" in result.output
        assert "API Error" in result.output


def test_invalid_repo_format(runner):
    """Test validation of repository format"""
    result = runner.invoke(
        cli,
        [
            "--token",
            "test-token",
            "update",
            "invalid-repo",  # Missing owner/repo format
            "test.txt",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid repository format" in result.output


def test_missing_file(runner):
    """Test handling of missing files"""
    result = runner.invoke(
        cli, ["--token", "test-token", "update", "owner/repo", "nonexistent.txt"]
    )

    assert result.exit_code != 0
    assert "File not found" in result.output


def test_update_files_read_error(runner, mock_supersonic):
    """Test error handling when reading files fails"""
    with runner.isolated_filesystem():
        # Create one file but reference two
        Path("file1.txt").write_text("content 1")

        result = runner.invoke(
            cli,
            [
                "--token",
                "test-token",
                "update-files",
                "owner/repo",
                "-f",
                "file1.txt",
                "path/to/file1.txt",
                "-f",
                "missing.txt",
                "path/to/file2.txt",
            ],
        )

        assert result.exit_code != 0
        assert "Failed to read file missing.txt" in result.output
