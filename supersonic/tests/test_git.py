import pytest
from unittest.mock import Mock, patch
from supersonic.utils.git import GitHandler


@pytest.fixture
def git_handler():
    with patch("supersonic.utils.git.Github") as mock_github:
        mock_github.return_value.get_repo = Mock()
        return GitHandler(token="test-token")


def test_create_branch(git_handler):
    """Test branch creation"""
    with patch("supersonic.utils.git.requests.post") as mock_post:
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        mock_repo = Mock()
        mock_branch = Mock()
        mock_branch.commit.sha = "test-sha"
        mock_repo.get_branch.return_value = mock_branch
        git_handler.github.get_repo.return_value = mock_repo
        
        git_handler.create_branch("owner/repo", "new-branch", "main")
        
        mock_repo.get_branch.assert_called_with("main")
        mock_post.assert_called_once()


def test_get_local_diff(git_handler, tmp_path):
    """Test getting diff from local repo"""
    with patch("supersonic.utils.git.Repo") as mock_repo:
        mock_repo.return_value.git.diff.return_value = "test diff"

        diff = git_handler.get_local_diff(tmp_path)
        assert diff == "test diff"
        mock_repo.return_value.git.diff.assert_called_with("HEAD")
