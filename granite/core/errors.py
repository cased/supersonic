class GraniteError(Exception):
    """Base exception for all Granite errors"""
    pass

class GitHubError(GraniteError):
    """Raised when GitHub API operations fail"""
    pass

class DiffError(GraniteError):
    """Raised when diff parsing or application fails"""
    pass

class ConfigError(GraniteError):
    """Raised when configuration is invalid"""
    pass

class LLMError(GraniteError):
    """Raised when LLM operations fail"""
    pass

class GitError(GraniteError):
    """Raised when git operations fail"""
    pass