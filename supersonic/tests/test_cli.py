import pytest
from click.testing import CliRunner
from unittest.mock import patch
from supersonic.cli import cli


@pytest.fixture
def runner():
    """Create CLI test runner"""
    return CliRunner()


@pytest.fixture
def mock_supersonic():
    """Mock Supersonic class"""
    with patch("supersonic.cli.Supersonic") as mock:
        instance = mock.return_value
        instance.create_pr_from_file.return_value = "https://github.com/test/pr/1"
        instance.create_pr_from_content.return_value = "https://github.com/test/pr/1"
        instance.create_pr_from_files.return_value = "https://github.com/test/pr/1"
        yield instance


def test_update_command(runner, mock_supersonic, tmp_path):
    """Test update command with file"""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    result = runner.invoke(
        cli,
        [
            "--token",
            "test-token",
            "update",
            "owner/repo",
            str(test_file),
            "docs/test.txt",
            "--title",
            "Test PR",
        ],
    )

    assert result.exit_code == 0
    assert "Created PR: https://github.com/test/pr/1" in result.output
    mock_supersonic.create_pr_from_file.assert_called_once()


def test_update_content_command(runner, mock_supersonic):
    """Test update-content command"""
    result = runner.invoke(
        cli,
        [
            "--token",
            "test-token",
            "update-content",
            "owner/repo",
            "test content",
            "test.txt",
            "--title",
            "Test PR",
        ],
    )

    assert result.exit_code == 0
    assert "Created PR: https://github.com/test/pr/1" in result.output
    mock_supersonic.create_pr_from_content.assert_called_once()


def test_update_files_command(runner, mock_supersonic, tmp_path):
    """Test update-files command"""
    file1 = tmp_path / "test1.txt"
    file1.write_text("content1")
    file2 = tmp_path / "test2.txt"
    file2.write_text("content2")

    result = runner.invoke(
        cli,
        [
            "--token",
            "test-token",
            "update-files",
            "owner/repo",
            "-f",
            str(file1),
            "docs/test1.txt",
            "-f",
            str(file2),
            "docs/test2.txt",
            "--title",
            "Test PR",
        ],
    )

    assert result.exit_code == 0
    assert "Created PR: https://github.com/test/pr/1" in result.output
    mock_supersonic.create_pr_from_files.assert_called_once()


def test_invalid_repo_format(runner):
    """Test error on invalid repo format"""
    result = runner.invoke(
        cli, ["--token", "test-token", "update", "invalid-repo", "test.txt"]
    )

    assert result.exit_code != 0
    assert "Invalid repository format" in result.output


def test_missing_file(runner):
    """Test error on missing file"""
    result = runner.invoke(
        cli, ["--token", "test-token", "update", "owner/repo", "nonexistent.txt"]
    )

    assert result.exit_code != 0
    assert "File not found" in result.output
