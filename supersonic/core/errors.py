class SupersonicError(Exception):
    """Base exception for all Supersonic errors"""

    pass


class GitHubError(SupersonicError):
    """Raised when GitHub API operations fail"""

    pass


class DiffError(SupersonicError):
    """Raised when diff parsing or application fails"""

    pass


class ConfigError(SupersonicError):
    """Raised when configuration is invalid"""

    pass


class LLMError(SupersonicError):
    """Raised when LLM operations fail"""

    pass


class GitError(SupersonicError):
    """Raised when git operations fail"""

    pass
