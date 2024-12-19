import pytest
from unittest.mock import patch, ANY
from supersonic.core.pr import Supersonic
from supersonic.core.config import SupersonicConfig, PRConfig
from supersonic.core.errors import GitHubError


@pytest.fixture
def mock_github():
    """Mock GitHub API with all required methods"""
    with patch("supersonic.core.pr.GitHubAPI") as mock:
        instance = mock.return_value
        instance.create_pull_request.return_value = "https://github.com/test/pr/1"
        instance.create_branch.return_value = None
        instance.update_file.return_value = None
        instance.add_labels.return_value = None
        instance.add_reviewers.return_value = None
        instance.enable_auto_merge.return_value = None
        yield instance


@pytest.fixture
def supersonic(mock_github):
    """Create Supersonic instance with mocked GitHub API"""
    config = SupersonicConfig(github_token="test-token")
    instance = Supersonic(config)
    instance.github = mock_github
    return instance


def test_create_pr_from_file(supersonic, tmp_path):
    """Test creating PR from a single local file"""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    url = supersonic.create_pr_from_file(
        repo="owner/repo",
        local_file_path=str(test_file),
        upstream_path="docs/test.txt",
        title="Update doc",
        base_branch="develop",
        labels=["documentation"]
    )

    assert url == "https://github.com/test/pr/1"
    
    supersonic.github.create_branch.assert_called_once_with(
        repo="owner/repo",
        branch=ANY,
        base_branch="develop"
    )
    supersonic.github.update_file.assert_called_once_with(
        repo="owner/repo",
        path="docs/test.txt",
        content="test content",
        message="Update docs/test.txt",
        branch=ANY
    )
    supersonic.github.create_pull_request.assert_called_once_with(
        repo="owner/repo",
        title="Update doc",
        body="",
        head=ANY,
        base="develop",
        draft=False
    )
    supersonic.github.add_labels.assert_called_once_with(
        "owner/repo", 1, ["documentation"]
    )


def test_create_pr_from_content_with_kwargs(supersonic):
    """Test creating PR from content using kwargs config"""
    url = supersonic.create_pr_from_content(
        repo="owner/repo",
        content="test content",
        path="test.txt",
        title="Add test file",
        description="Adding a test file",
        base_branch="develop",
        draft=True,
        labels=["test"],
        reviewers=["reviewer1"]
    )

    assert url == "https://github.com/test/pr/1"
    
    supersonic.github.create_branch.assert_called_once_with(
        repo="owner/repo",
        branch=ANY,
        base_branch="develop"
    )
    supersonic.github.create_pull_request.assert_called_once_with(
        repo="owner/repo",
        title="Add test file",
        body="Adding a test file",
        head=ANY,
        base="develop",
        draft=True
    )
    supersonic.github.add_labels.assert_called_once_with(
        "owner/repo", 1, ["test"]
    )
    supersonic.github.add_reviewers.assert_called_once_with(
        "owner/repo", 1, ["reviewer1"]
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
        title="Multiple updates",
        base_branch="develop"
    )

    assert url == "https://github.com/test/pr/1"
    
    supersonic.github.create_branch.assert_called_once_with(
        repo="owner/repo",
        branch=ANY,
        base_branch="develop"
    )

    # Verify two file updates occurred
    assert supersonic.github.update_file.call_count == 2
    calls = supersonic.github.update_file.call_args_list
    assert any(
        call.kwargs["path"] == "test1.txt" and 
        call.kwargs["content"] == "content 1" and
        call.kwargs["repo"] == "owner/repo"
        for call in calls
    )
    assert any(
        call.kwargs["path"] == "test2.txt" and 
        call.kwargs["content"] == "content 2" and
        call.kwargs["repo"] == "owner/repo"
        for call in calls
    )


def test_create_pr_using_config_object(supersonic):
    """Test using PRConfig object with direct create_pr call"""
    config = PRConfig(
        title="PR Title",
        description="Test description",
        base_branch="develop",
        draft=True,
        labels=["feature"],
        reviewers=["reviewer1"],
        auto_merge=True,
        merge_strategy="squash"
    )

    url = supersonic.create_pr(
        repo="owner/repo",
        changes={"test.txt": "test content"},
        config=config
    )

    assert url == "https://github.com/test/pr/1"
    
    supersonic.github.create_branch.assert_called_once_with(
        repo="owner/repo",
        branch=ANY,
        base_branch="develop"
    )
    supersonic.github.create_pull_request.assert_called_once_with(
        repo="owner/repo",
        title="PR Title",
        body="Test description",
        head=ANY,
        base="develop",
        draft=True
    )
    supersonic.github.add_labels.assert_called_once_with(
        "owner/repo", 1, ["feature"]
    )
    supersonic.github.add_reviewers.assert_called_once_with(
        "owner/repo", 1, ["reviewer1"]
    )
    supersonic.github.enable_auto_merge.assert_called_once_with(
        repo="owner/repo",
        pr_number=1,
        merge_method="squash"
    )


def test_create_pr_mixing_config_and_kwargs(supersonic):
    """Test that mixing PRConfig and kwargs raises error"""
    config = PRConfig(
        title="Original Title", 
        base_branch="main"
    )
    
    with pytest.raises(ValueError, match="Cannot provide both PRConfig and keyword arguments"):
        supersonic.create_pr(
            repo="owner/repo",
            changes={"test.txt": "content"},
            config=config,
            title="New Title"  # Attempting to mix with kwargs
        )


def test_create_pr_using_dict_config(supersonic):
    """Test passing config as a dictionary"""
    config = {
        "title": "Dict Config",
        "description": "Created from dict",
        "base_branch": "develop",
        "labels": ["test"],
        "reviewers": ["reviewer1"]
    }

    url = supersonic.create_pr(
        repo="owner/repo",
        changes={"test.txt": "content"},
        config=config
    )

    assert url == "https://github.com/test/pr/1"
    supersonic.github.create_pull_request.assert_called_once_with(
        repo="owner/repo",
        title="Dict Config",
        body="Created from dict",
        head=ANY,
        base="develop",
        draft=False
    )
    supersonic.github.add_labels.assert_called_once_with(
        "owner/repo", 1, ["test"]
    )


def test_create_pr_kwargs_ordering(supersonic):
    """Test that kwargs order doesn't matter"""
    url1 = supersonic.create_pr_from_content(
        repo="owner/repo",
        content="test content",
        path="test.txt",
        title="Test",
        labels=["bug"],
        base_branch="develop"
    )

    # Reset mock
    supersonic.github.reset_mock()

    # Same args, different order
    url2 = supersonic.create_pr_from_content(
        base_branch="develop",
        labels=["bug"],
        title="Test",
        repo="owner/repo",
        path="test.txt",
        content="test content"
    )

    assert url1 == url2
    supersonic.github.create_pull_request.assert_called_once_with(
        repo="owner/repo",
        title="Test",
        body="",
        head=ANY,
        base="develop",
        draft=False
    )


def test_create_pr_defaults(supersonic):
    """Test that default config values are used when not specified"""
    url = supersonic.create_pr_from_content(
        repo="owner/repo",
        content="test content",
        path="test.txt"
    )

    assert url == "https://github.com/test/pr/1"
    
    supersonic.github.create_branch.assert_called_once_with(
        repo="owner/repo",
        branch=ANY,
        base_branch="main"  # Default base branch
    )
    supersonic.github.create_pull_request.assert_called_once_with(
        repo="owner/repo",
        title=ANY,
        body="",
        head=ANY,
        base="main",
        draft=False
    )


def test_create_pr_empty_lists(supersonic):
    """Test PR creation with empty lists for labels and reviewers"""
    url = supersonic.create_pr_from_content(
        repo="owner/repo",
        content="test content",
        path="test.txt",
        labels=[],
        reviewers=[]
    )

    assert url == "https://github.com/test/pr/1"
    # Should not call add_labels or add_reviewers with empty lists
    supersonic.github.add_labels.assert_not_called()
    supersonic.github.add_reviewers.assert_not_called()


def test_create_pr_error_handling(supersonic, tmp_path):
    """Test error handling in PR creation"""
    with pytest.raises(GitHubError, match="Failed to update file"):
        supersonic.create_pr_from_file(
            repo="owner/repo",
            local_file_path=str(tmp_path / "nonexistent.txt"),
            upstream_path="test.txt",
        )


def test_create_pr_unknown_kwargs(supersonic):
    """Test that unknown kwargs get handled gracefully"""
    url = supersonic.create_pr_from_content(
        repo="owner/repo",
        content="test content",
        path="test.txt",
        title="Test",
        unknown_param="value",  # Should be ignored
        another_unknown=123     # Should be ignored
    )

    assert url == "https://github.com/test/pr/1"
    supersonic.github.create_pull_request.assert_called_once_with(
        repo="owner/repo",
        title="Test",
        body="",
        head=ANY,
        base="main",
        draft=False
    )