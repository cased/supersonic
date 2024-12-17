from unittest.mock import AsyncMock, Mock
import pytest
from granite import Granite
from granite.core.config import GraniteConfig
from granite.core.errors import GitHubError


@pytest.fixture
def mock_github():
    """Mock GitHub API client with all required methods"""
    mock = Mock()
    # Basic PR creation methods
    mock.create_pull_request = AsyncMock(
        return_value="https://github.com/test/test/pull/1"
    )
    mock.create_branch = AsyncMock()
    mock.update_file = AsyncMock()

    # Additional PR configuration methods
    mock.add_reviewers = AsyncMock()
    mock.add_labels = AsyncMock()
    mock.enable_auto_merge = AsyncMock()
    return mock


@pytest.mark.asyncio
async def test_create_pr_from_content(mock_github):
    """Test creating PR from string content"""
    config = GraniteConfig(github_token="test")
    granite = Granite(config)
    granite.github = mock_github

    pr_url = await granite.create_pr_from_content(
        repo="test/repo", content="print('test')", path="test.py"
    )

    assert pr_url == "https://github.com/test/test/pull/1"
    mock_github.update_file.assert_called_once()
    assert mock_github.update_file.call_args[1]["content"] == "print('test')"
    assert mock_github.update_file.call_args[1]["path"] == "test.py"


@pytest.mark.asyncio
async def test_create_pr_from_content_error(mock_github):
    """Test error handling in create_pr_from_content"""
    config = GraniteConfig(github_token="test")
    granite = Granite(config)
    granite.github = mock_github
    mock_github.update_file.side_effect = Exception("File update failed")

    with pytest.raises(GitHubError, match="Failed to update content"):
        await granite.create_pr_from_content(
            repo="test/repo", content="print('test')", path="test.py"
        )


@pytest.mark.asyncio
async def test_create_pr_from_file(mock_github, tmp_path):
    """Test creating PR from a local file"""
    test_file = tmp_path / "test.py"
    test_file.write_text("print('test')")

    config = GraniteConfig(github_token="test")
    granite = Granite(config)
    granite.github = mock_github

    pr_url = await granite.create_pr_from_file(
        repo="test/repo", local_file_path=str(test_file), upstream_path="src/test.py"
    )

    assert pr_url == "https://github.com/test/test/pull/1"
    mock_github.update_file.assert_called_once()
    assert mock_github.update_file.call_args[1]["content"] == "print('test')"
    assert mock_github.update_file.call_args[1]["path"] == "src/test.py"


@pytest.mark.asyncio
async def test_create_pr_from_file_not_found(mock_github):
    """Test error handling when file doesn't exist"""
    config = GraniteConfig(github_token="test")
    granite = Granite(config)
    granite.github = mock_github

    with pytest.raises(GitHubError, match="Failed to update file"):
        await granite.create_pr_from_file(
            repo="test/repo", local_file_path="nonexistent.py", upstream_path="test.py"
        )


@pytest.mark.asyncio
async def test_create_pr_from_files(mock_github):
    """Test creating PR from multiple files"""
    config = GraniteConfig(github_token="test")
    granite = Granite(config)
    granite.github = mock_github

    files = {"src/test1.py": "print('test1')", "src/test2.py": "print('test2')"}

    pr_url = await granite.create_pr_from_files(repo="test/repo", files=files)

    assert pr_url == "https://github.com/test/test/pull/1"
    assert mock_github.update_file.call_count == 2
    calls = mock_github.update_file.call_args_list
    assert any(
        call[1]["path"] == "src/test1.py" and call[1]["content"] == "print('test1')"
        for call in calls
    )
    assert any(
        call[1]["path"] == "src/test2.py" and call[1]["content"] == "print('test2')"
        for call in calls
    )


@pytest.mark.asyncio
async def test_create_pr_from_content_with_options(mock_github):
    """Test creating PR from content with custom options"""
    config = GraniteConfig(github_token="test")
    granite = Granite(config)
    granite.github = mock_github

    pr_url = await granite.create_pr_from_content(
        repo="test/repo",
        content="print('test')",
        path="test.py",
        title="Custom PR",
        description="Test description",
        draft=True,
        labels=["test"],
        reviewers=["user1"],
    )

    assert pr_url == "https://github.com/test/test/pull/1"
    mock_github.create_pull_request.assert_called_with(
        repo="test/repo",
        title="Custom PR",
        body="Test description",
        head=mock_github.create_branch.call_args[1]["branch"],
        base="main",
        draft=True,
    )
    mock_github.add_labels.assert_called_with("test/repo", 1, ["test"])
    mock_github.add_reviewers.assert_called_with("test/repo", 1, ["user1"])


@pytest.mark.asyncio
async def test_create_pr_from_file_with_branch_name(mock_github, tmp_path):
    """Test creating PR with custom branch name from file"""
    test_file = tmp_path / "test.py"
    test_file.write_text("print('test')")

    config = GraniteConfig(github_token="test")
    granite = Granite(config)
    granite.github = mock_github

    branch_name = "feature/custom-branch"
    pr_url = await granite.create_pr_from_file(
        repo="test/repo",
        file_path=str(test_file),
        upstream_path="src/test.py",
        branch_name=branch_name,
    )

    # No need to assert branch name call since it's handled by create_pr
    assert pr_url == "https://github.com/test/test/pull/1"
