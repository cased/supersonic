import pytest
from unittest.mock import patch
from supersonic.core.pr import Supersonic
from supersonic.core.config import PRConfig
from supersonic.core.errors import GitHubError


@pytest.fixture
def mock_github():
    """Mock GitHub API"""
    with patch("supersonic.core.pr.GitHubAPI") as mock:
        yield mock.return_value


@pytest.fixture
def supersonic(mock_github):
    """Create Supersonic instance with mocked GitHub API"""
    return Supersonic("test-token")


def test_create_pr_basic(supersonic, mock_github):
    """Test basic PR creation"""
    mock_github.create_pull_request.return_value = "https://github.com/owner/repo/pull/1"

    url = supersonic.create_pr(
        repo="owner/repo",
        changes={"test.txt": "content"},
        title="Test PR"
    )

    assert url == "https://github.com/owner/repo/pull/1"
    mock_github.create_branch.assert_called_once()
    mock_github.update_file.assert_called_once_with(
        repo="owner/repo",
        path="test.txt",
        content="content",
        message="Update test.txt",
        branch=mock_github.create_branch.call_args[1]["branch"]
    )


def test_create_pr_with_config(supersonic, mock_github):
    """Test PR creation with custom config"""
    mock_github.create_pull_request.return_value = "https://github.com/owner/repo/pull/1"

    config = PRConfig(
        title="Custom PR",
        description="Test description",
        base_branch="develop",
        draft=True,
        labels=["test"],
        reviewers=["user1"]
    )

    url = supersonic.create_pr(
        repo="owner/repo",
        changes={"test.txt": "content"},
        config=config
    )

    assert url == "https://github.com/owner/repo/pull/1"
    mock_github.create_pull_request.assert_called_with(
        repo="owner/repo",
        title="Custom PR",
        body="Test description",
        head=mock_github.create_branch.call_args[1]["branch"],
        base="develop",
        draft=True
    )
    mock_github.add_labels.assert_called_with("owner/repo", 1, ["test"])
    mock_github.add_reviewers.assert_called_with("owner/repo", 1, ["user1"])


def test_create_pr_from_file(supersonic, mock_github, tmp_path):
    """Test creating PR from local file"""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    mock_github.create_pull_request.return_value = "https://github.com/owner/repo/pull/1"

    url = supersonic.create_pr_from_file(
        repo="owner/repo",
        local_file_path=str(test_file),
        upstream_path="docs/test.txt"
    )

    assert url == "https://github.com/owner/repo/pull/1"
    mock_github.update_file.assert_called_with(
        repo="owner/repo",
        path="docs/test.txt",
        content="test content",
        message="Update docs/test.txt",
        branch=mock_github.create_branch.call_args[1]["branch"]
    )


def test_create_pr_from_files(supersonic, mock_github):
    """Test creating PR from multiple files"""
    mock_github.create_pull_request.return_value = "https://github.com/owner/repo/pull/1"

    files = {
        "test1.txt": "content1",
        "test2.txt": "content2"
    }

    url = supersonic.create_pr_from_files(
        repo="owner/repo",
        files=files
    )

    assert url == "https://github.com/owner/repo/pull/1"
    assert mock_github.update_file.call_count == 2
    mock_github.create_pull_request.assert_called_once()


def test_create_pr_error(supersonic, mock_github):
    """Test error handling in PR creation"""
    mock_github.create_branch.side_effect = Exception("Branch creation failed")

    with pytest.raises(GitHubError, match="Failed to create PR"):
        supersonic.create_pr(
            repo="owner/repo",
            changes={"test.txt": "content"}
        )
