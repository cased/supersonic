import pytest
from unittest.mock import patch
from supersonic.core.pr import Supersonic
from supersonic.core.config import SupersonicConfig
from supersonic.core.errors import GitHubError


@pytest.fixture
def mock_github():
    """Mock GitHub API"""
    with patch("supersonic.core.pr.GitHubAPI") as mock:
        instance = mock.return_value
        instance.create_pr.return_value = "https://github.com/test/pr/1"
        yield instance


@pytest.fixture
def supersonic(mock_github):
    """Create Supersonic instance with mocked dependencies"""
    return Supersonic(SupersonicConfig(github_token="test-token"))


def test_create_pr_from_file(supersonic, tmp_path):
    """Test creating PR from a single local file"""
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    url = supersonic.create_pr_from_file(
        repo="owner/repo",
        local_file_path=str(test_file),
        upstream_path="docs/test.txt",
    )

    assert url == "https://github.com/test/pr/1"
    supersonic.github.create_pr.assert_called_once_with(
        repo="owner/repo",
        changes={"docs/test.txt": "test content"},
        config={},
    )


def test_create_pr_from_content(supersonic):
    """Test creating PR from content string"""
    url = supersonic.create_pr_from_content(
        repo="owner/repo",
        content="test content",
        path="test.txt",
    )

    assert url == "https://github.com/test/pr/1"
    supersonic.github.create_pr.assert_called_once_with(
        repo="owner/repo",
        changes={"test.txt": "test content"},
        config={},
    )


def test_create_pr_from_multiple_contents(supersonic):
    """Test creating PR from multiple content strings"""
    contents = {
        "test1.txt": "content 1",
        "test2.txt": "content 2",
    }

    url = supersonic.create_pr_from_multiple_contents(
        repo="owner/repo",
        contents=contents,
    )

    assert url == "https://github.com/test/pr/1"
    supersonic.github.create_pr.assert_called_once_with(
        repo="owner/repo",
        changes=contents,
        config={},
    )


def test_create_pr_from_files(supersonic, tmp_path):
    """Test creating PR from multiple local files"""
    # Create test files
    file1 = tmp_path / "test1.txt"
    file2 = tmp_path / "test2.txt"
    file1.write_text("content 1")
    file2.write_text("content 2")

    files = {
        str(file1): "docs/test1.txt",
        str(file2): "docs/test2.txt",
    }

    url = supersonic.create_pr_from_files(
        repo="owner/repo",
        files=files,
    )

    assert url == "https://github.com/test/pr/1"
    supersonic.github.create_pr.assert_called_once_with(
        repo="owner/repo",
        changes={
            "docs/test1.txt": "content 1",
            "docs/test2.txt": "content 2",
        },
        config={},
    )


def test_create_pr_from_files_missing_file(supersonic, tmp_path):
    """Test error when local file doesn't exist"""
    with pytest.raises(GitHubError, match="Failed to read file"):
        supersonic.create_pr_from_files(
            repo="owner/repo",
            files={"nonexistent.txt": "test.txt"},
        )


def test_create_pr_with_options(supersonic, tmp_path):
    """Test creating PR with additional options"""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    url = supersonic.create_pr_from_file(
        repo="owner/repo",
        local_file_path=str(test_file),
        upstream_path="test.txt",
        title="Test PR",
        draft=True,
        labels=["test"],
    )

    assert url == "https://github.com/test/pr/1"
    supersonic.github.create_pr.assert_called_once_with(
        repo="owner/repo",
        changes={"test.txt": "test content"},
        config={"title": "Test PR", "draft": True, "labels": ["test"]},
    )


def test_create_pr_with_config_object(supersonic):
    """Test creating PR with PRConfig object"""
    from supersonic.core.config import PRConfig
    
    config = PRConfig(
        title="Test PR",
        description="Test description",
        draft=True,
        labels=["test"],
        reviewers=["user1"],
    )
    
    url = supersonic.create_pr_from_content(
        repo="owner/repo",
        content="test content",
        path="test.txt",
        config=config,
    )
    
    assert url == "https://github.com/test/pr/1"
    supersonic.github.create_pr.assert_called_once_with(
        repo="owner/repo",
        changes={"test.txt": "test content"},
        config={"title": "Test PR", "description": "Test description", 
               "draft": True, "labels": ["test"], "reviewers": ["user1"]},
    )


def test_create_pr_error_handling(supersonic, tmp_path):
    """Test error handling in PR creation"""
    with pytest.raises(GitHubError, match="Failed to update file"):
        supersonic.create_pr_from_file(
            repo="owner/repo",
            local_file_path=str(tmp_path / "nonexistent.txt"),
            upstream_path="test.txt",
        )


def test_create_pr_with_auto_merge(supersonic):
    """Test creating PR with auto-merge enabled"""
    url = supersonic.create_pr_from_content(
        repo="owner/repo",
        content="test content",
        path="test.txt",
        auto_merge=True,
        merge_strategy="squash",
    )
    
    assert url == "https://github.com/test/pr/1"
    # Verify auto-merge was enabled
    supersonic.github.enable_auto_merge.assert_called_once_with(
        repo="owner/repo",
        pr_number=1,
        merge_method="squash",
    )


def test_create_pr_with_team_reviewers(supersonic):
    """Test creating PR with team reviewers"""
    url = supersonic.create_pr_from_content(
        repo="owner/repo",
        content="test content",
        path="test.txt",
        team_reviewers=["team1", "team2"],
    )
    
    assert url == "https://github.com/test/pr/1"
    # Verify team reviewers were added
    supersonic.github.add_team_reviewers.assert_called_once_with(
        repo="owner/repo",
        pr_number=1,
        team_reviewers=["team1", "team2"],
    )
