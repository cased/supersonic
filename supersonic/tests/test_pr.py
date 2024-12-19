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
        instance.create_pull_request.return_value = "https://github.com/owner/repo/pull/1"
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


def test_create_pr_from_file(mock_github, tmp_path):
    """Test creating PR from file"""
    supersonic = Supersonic(config=SupersonicConfig(github_token="test"))
    
    # Create the test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    url = supersonic.create_pr_from_file(
        repo="owner/repo",
        local_file_path=str(test_file),
        upstream_path="path/to/test.txt",
        title="Test PR",  # Required
        draft=False,
    )
    assert url == "https://github.com/owner/repo/pull/1"


def test_create_pr_from_content_with_kwargs(mock_github):
    """Test creating PR from content with kwargs"""
    supersonic = Supersonic(config=SupersonicConfig(github_token="test"))
    
    url = supersonic.create_pr_from_content(
        repo="owner/repo",
        content="test content",
        upstream_path="test.txt",
        title="Test PR",
        draft=False,
    )
    assert url == "https://github.com/owner/repo/pull/1"


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
        base_branch="develop",
    )

    assert url == "https://github.com/owner/repo/pull/1"

    supersonic.github.create_branch.assert_called_once_with(
        repo="owner/repo", branch=ANY, base_branch="develop"
    )

    # Verify two file updates occurred
    assert supersonic.github.update_file.call_count == 2
    calls = supersonic.github.update_file.call_args_list
    assert any(
        call.kwargs["path"] == "test1.txt"
        and call.kwargs["content"] == "content 1"
        and call.kwargs["repo"] == "owner/repo"
        for call in calls
    )
    assert any(
        call.kwargs["path"] == "test2.txt"
        and call.kwargs["content"] == "content 2"
        and call.kwargs["repo"] == "owner/repo"
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
        merge_strategy="squash",
    )

    url = supersonic.create_pr(
        repo="owner/repo", changes={"test.txt": "test content"}, config=config
    )

    assert url == "https://github.com/owner/repo/pull/1"

    supersonic.github.create_branch.assert_called_once_with(
        repo="owner/repo", branch=ANY, base_branch="develop"
    )
    supersonic.github.create_pull_request.assert_called_once_with(
        repo="owner/repo",
        title="PR Title",
        body="Test description",
        head=ANY,
        base="develop",
        draft=True,
    )
    supersonic.github.add_labels.assert_called_once_with("owner/repo", 1, ["feature"])
    supersonic.github.add_reviewers.assert_called_once_with(
        "owner/repo", 1, ["reviewer1"]
    )
    supersonic.github.enable_auto_merge.assert_called_once_with(
        repo="owner/repo", pr_number=1, merge_method="squash"
    )


def test_create_pr_mixing_config_and_kwargs(supersonic):
    """Test that mixing PRConfig and kwargs raises error"""
    config = PRConfig(title="Original Title", base_branch="main")

    with pytest.raises(
        ValueError, match="Cannot provide both PRConfig and keyword arguments"
    ):
        supersonic.create_pr(
            repo="owner/repo",
            changes={"test.txt": "content"},
            config=config,
            title="New Title",  # Attempting to mix with kwargs
        )


def test_create_pr_using_dict_config(supersonic):
    """Test passing config as a dictionary"""
    config = {
        "title": "Dict Config",
        "description": "Created from dict",
        "base_branch": "develop",
        "labels": ["test"],
        "reviewers": ["reviewer1"],
    }

    url = supersonic.create_pr(
        repo="owner/repo", changes={"test.txt": "content"}, config=config
    )

    assert url == "https://github.com/owner/repo/pull/1"
    supersonic.github.create_pull_request.assert_called_once_with(
        repo="owner/repo",
        title="Dict Config",
        body="Created from dict",
        head=ANY,
        base="develop",
        draft=False,
    )
    supersonic.github.add_labels.assert_called_once_with("owner/repo", 1, ["test"])


def test_create_pr_kwargs_ordering(mock_github):
    """Test PR creation with kwargs in different order"""
    supersonic = Supersonic(config=SupersonicConfig(github_token="test"))
    
    url = supersonic.create_pr_from_content(
        content="test content",
        repo="owner/repo",
        upstream_path="test.txt",
        title="Test PR",
    )
    assert url == "https://github.com/owner/repo/pull/1"


def test_create_pr_defaults(mock_github):
    """Test PR creation with default values"""
    supersonic = Supersonic(config=SupersonicConfig(
        github_token="test",
        default_pr_config=PRConfig(title="Default Title")  # Add default title
    ))
    
    url = supersonic.create_pr_from_content(
        repo="owner/repo",
        content="test content",
        upstream_path="test.txt",
    )
    assert url == "https://github.com/owner/repo/pull/1"


def test_create_pr_empty_lists(mock_github):
    """Test PR creation with empty lists"""
    supersonic = Supersonic(config=SupersonicConfig(github_token="test"))
    
    url = supersonic.create_pr_from_content(
        repo="owner/repo",
        content="test content",
        upstream_path="test.txt",
        title="Test PR",
    )
    assert url == "https://github.com/owner/repo/pull/1"


def test_create_pr_unknown_kwargs(mock_github):
    """Test PR creation with unknown kwargs"""
    supersonic = Supersonic(config=SupersonicConfig(github_token="test"))
    
    with pytest.raises(ValueError):
        supersonic.create_pr_from_content(
            repo="owner/repo",
            content="test content",
            upstream_path="test.txt",
            unknown_kwarg="value",  # This should raise an error
        )


def test_create_pr_error_handling(supersonic, tmp_path):
    """Test error handling in PR creation"""
    with pytest.raises(GitHubError, match="Failed to update file"):
        supersonic.create_pr_from_file(
            repo="owner/repo",
            local_file_path=str(tmp_path / "nonexistent.txt"),
            upstream_path="test.txt",
        )
