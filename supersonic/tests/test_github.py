import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, PropertyMock
from supersonic.core.github import GitHubAPI
from supersonic.core.errors import GitHubError


class MockResponse:
    """Helper class for mocked HTTP responses"""

    def __init__(self, status=200, text="OK"):
        self.status = status
        self._text = text

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_gh_repo():
    """Mock GitHub Repository object"""
    repo = Mock()
    repo.create_git_ref = Mock()
    repo.get_git_ref = Mock()
    repo.get_contents = Mock()
    repo.create_file = Mock()
    repo.update_file = Mock()
    repo.delete_file = Mock()
    repo.create_pull = Mock()
    repo.get_pull = Mock()
    return repo


@pytest.fixture
def mock_gh():
    """Mock Github client"""
    with patch("supersonic.core.github.Github", autospec=True) as mock_github:
        yield mock_github.return_value


@pytest_asyncio.fixture
async def github_api(mock_gh, mock_gh_repo):
    """Create GitHubAPI instance with mocked dependencies"""
    mock_gh.get_repo = Mock(return_value=mock_gh_repo)

    api = GitHubAPI(token="test-token")

    mock_session = AsyncMock()
    mock_session.closed = False
    mock_session.put = Mock(return_value=MockResponse())

    api._session = mock_session
    return api


@pytest.mark.asyncio
async def test_create_branch(github_api, mock_gh_repo):
    """Test branch creation"""
    base_ref = Mock()
    base_ref.object.sha = "base-sha"
    mock_gh_repo.get_git_ref.return_value = base_ref

    await github_api.create_branch("owner/repo", "new-branch", "main")

    mock_gh_repo.get_git_ref.assert_called_with("heads/main")
    mock_gh_repo.create_git_ref.assert_called_with(
        ref="refs/heads/new-branch", sha="base-sha"
    )


@pytest.mark.asyncio
async def test_create_branch_exists(github_api, mock_gh_repo):
    """Test branch creation when branch already exists"""
    base_ref = Mock()
    base_ref.object.sha = "base-sha"
    branch_ref = Mock()
    mock_gh_repo.get_git_ref.side_effect = [base_ref, branch_ref]
    mock_gh_repo.create_git_ref.side_effect = Exception("Reference already exists")

    await github_api.create_branch("owner/repo", "existing-branch", "main")

    assert mock_gh_repo.get_git_ref.call_count == 2
    branch_ref.edit.assert_called_with("base-sha", force=True)


@pytest.mark.asyncio
async def test_update_file_create(github_api, mock_gh_repo):
    """Test file creation through update_file"""
    mock_gh_repo.get_contents.side_effect = Exception("Not Found")

    await github_api.update_file(
        repo="owner/repo",
        path="test.txt",
        content="test content",
        message="Add test file",
        branch="main",
    )

    mock_gh_repo.create_file.assert_called_with(
        path="test.txt", message="Add test file", content="test content", branch="main"
    )


@pytest.mark.asyncio
async def test_update_file_update(github_api, mock_gh_repo):
    """Test file update through update_file"""
    contents = Mock()
    contents.sha = "file-sha"
    mock_gh_repo.get_contents.return_value = contents

    await github_api.update_file(
        repo="owner/repo",
        path="test.txt",
        content="updated content",
        message="Update test file",
        branch="main",
    )

    mock_gh_repo.update_file.assert_called_with(
        path="test.txt",
        message="Update test file",
        content="updated content",
        sha="file-sha",
        branch="main",
    )


@pytest.mark.asyncio
async def test_update_file_delete(github_api, mock_gh_repo):
    """Test file deletion through update_file"""
    contents = Mock()
    contents.sha = "file-sha"
    mock_gh_repo.get_contents.return_value = contents

    await github_api.update_file(
        repo="owner/repo",
        path="test.txt",
        content=None,  # None indicates deletion
        message="Delete test file",
        branch="main",
    )

    mock_gh_repo.delete_file.assert_called_with(
        path="test.txt", message="Delete test file", sha="file-sha", branch="main"
    )


@pytest.mark.asyncio
async def test_create_pull_request(github_api, mock_gh_repo):
    """Test pull request creation"""
    mock_pr = Mock()
    type(mock_pr).html_url = PropertyMock(
        return_value="https://github.com/owner/repo/pull/1"
    )
    mock_gh_repo.create_pull.return_value = mock_pr

    url = await github_api.create_pull_request(
        repo="owner/repo",
        title="Test PR",
        body="Test description",
        head="feature",
        base="main",
    )

    assert url == "https://github.com/owner/repo/pull/1"
    mock_gh_repo.create_pull.assert_called_with(
        title="Test PR",
        body="Test description",
        head="feature",
        base="main",
        draft=False,
    )


@pytest.mark.asyncio
async def test_add_labels(github_api, mock_gh_repo):
    """Test adding labels to PR"""
    mock_pr = Mock()
    mock_gh_repo.get_pull.return_value = mock_pr

    await github_api.add_labels(
        repo="owner/repo", pr_number=1, labels=["bug", "feature"]
    )

    mock_gh_repo.get_pull.assert_called_with(1)
    mock_pr.add_to_labels.assert_called_with("bug", "feature")


@pytest.mark.asyncio
async def test_add_reviewers(github_api, mock_gh_repo):
    """Test adding reviewers to PR"""
    mock_pr = Mock()
    mock_gh_repo.get_pull.return_value = mock_pr

    await github_api.add_reviewers(
        repo="owner/repo", pr_number=1, reviewers=["user1", "user2"]
    )

    mock_gh_repo.get_pull.assert_called_with(1)
    mock_pr.create_review_request.assert_called_with(reviewers=["user1", "user2"])


@pytest.mark.asyncio
async def test_enable_auto_merge(github_api):
    """Test enabling auto-merge"""
    await github_api.enable_auto_merge(
        repo="owner/repo", pr_number=1, merge_method="squash"
    )

    github_api._session.put.assert_called_with(
        "https://api.github.com/repos/owner/repo/pulls/1/auto_merge",
        json={"merge_method": "squash"},
    )


@pytest.mark.asyncio
async def test_enable_auto_merge_error(github_api):
    """Test enabling auto-merge with error response"""
    github_api._session.put = Mock(
        return_value=MockResponse(status=422, text="Auto-merge not allowed")
    )

    with pytest.raises(GitHubError, match="Failed to enable auto-merge"):
        await github_api.enable_auto_merge(
            repo="owner/repo", pr_number=1, merge_method="squash"
        )
